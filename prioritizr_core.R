# prioritizr_core.R -- shared engine for the sub-regional analyses (03a/03b/03c).
#
# One function per stage of the optimization, so each thin 03x notebook keeps cell-by-cell
# diagnostics (source() this, then call the pr_* functions in order). The engine hard-codes NO
# run parameter: everything comes from config.py via manifest.json (refreshed per-analysis by
# pr_refresh_manifest). The only spatial difference between analyses is the ROI crop(+mask) in
# pr_ingest and the lock-in source in pr_planning_units -- both driven by params.
#
# Context flow: each pr_* takes the accumulating `ctx` list and returns a list to merge in
#   ctx <- modifyList(ctx, pr_ingest(ctx))
# Ported cell-for-cell from the original 03_prioritizr.ipynb so 03a reproduces its result.

suppressPackageStartupMessages({
  library(prioritizr)
  library(terra)
  library(jsonlite)
})

# ---- Stage 0: refresh + read the manifest -------------------------------
pr_refresh_manifest <- function(proj, analysis) {
  # Regenerate manifest.json from config.py for THIS analysis, then confirm it exists.
  # A failed refresh STOPS the run rather than solving against a stale/other-analysis manifest.
  py       <- file.path(proj, ".venv", "bin", "python")
  manifest <- file.path(proj, "input_data", "aligned_stack", "manifest.json")
  if (file.exists(py)) {
    code <- sprintf("import config; print(config.write_manifest(analysis='%s'))", analysis)
    out  <- suppressWarnings(system2(py, c("-c", shQuote(code)), stdout = TRUE, stderr = TRUE))
    st   <- attr(out, "status")
    if (!is.null(st) && st != 0)
      stop(sprintf("manifest refresh FAILED for analysis '%s' (config.py error, or a required\n  input vector is missing -- e.g. the ab_foothills boundary/foothills gpkg):\n  %s",
                   analysis, paste(out, collapse = "\n  ")))
    cat(sprintf("manifest refreshed from config.py (analysis=%s)\n", analysis))
  } else {
    cat(sprintf("NOTE: %s not found -- using the existing manifest as-is\n", py))
  }
  stopifnot("manifest.json not found -- run 02 to build the aligned stack first" = file.exists(manifest))
  manifest
}

# ---- Stage 1: setup -- unpack params/grid/layers + banner ---------------
pr_setup <- function(manifest_path, proj) {
  manifest <- jsonlite::read_json(manifest_path, simplifyVector = TRUE)
  params <- manifest$params; grid <- manifest$grid; layers <- manifest$layers

  RUN_TAG <- params$results_subdir
  OUT_DIR <- file.path(proj, params$results_dir, RUN_TAG)
  dir.create(OUT_DIR, recursive = TRUE, showWarnings = FALSE)

  use_portfolio <- identical(params$solver, "gurobi")     # gap-portfolio only with Gurobi
  have_gurobi   <- requireNamespace("gurobi", quietly = TRUE)

  agg <- params$prototype_agg_factor
  roi <- params$roi
  cat(sprintf("prioritizr %s | terra %s | analysis=%s | solver=%s%s\n",
              packageVersion("prioritizr"), packageVersion("terra"), params$analysis, params$solver,
              if (use_portfolio) sprintf(" (gap-portfolio n=%d)", params$portfolio_n) else " (single solution)"))
  cat(sprintf("objective=%s | budget=%.0f%% target=%.0f%% | opt_gap=%.2f | time_limit=%ss\n",
              params$objective, 100 * params$budget_pct, 100 * params$target_pct,
              params$opt_gap, params$solver_time_limit))
  cat(sprintf("resolution: %d m (agg factor %d) | decisions=%s\n",
              grid$res_m * agg, agg, params$decision_type))
  cat(sprintf("roi: mode=%s%s | lock_in=%s\n", roi$mode,
              if (is.null(roi$bounds)) "" else sprintf(" bounds=[%s]%s",
                paste(round(unlist(roi$bounds)), collapse = ", "),
                if (is.null(roi$mask_path)) " (bbox)" else " (+mask)"),
              params$lock_in$source))
  cat(sprintf("penalties: connectivity=%g | boundary=%g | neighbor=%g\n",
              params$connectivity_penalty, params$boundary_penalty, params$neighbor_penalty))
  cat(sprintf("outputs -> %s\n", sub(paste0(proj, "/"), "", OUT_DIR)))

  list(proj = proj, params = params, grid = grid, layers = layers,
       out_dir = OUT_DIR, run_tag = RUN_TAG,
       use_portfolio = use_portfolio, have_gurobi = have_gurobi)
}

# ---- Stage 2: ingest -- rast + CROP(+mask) + relaxed validation + agg + normalize ----
pr_ingest <- function(ctx) {
  params <- ctx$params; grid <- ctx$grid; layers <- ctx$layers; proj <- ctx$proj
  abspath <- function(p) file.path(proj, p)

  is_cont <- layers$role == "feature_continuous"
  is_efg  <- layers$role == "feature_efg"
  feat_rows <- layers[is_cont | is_efg, ]
  cost_row  <- layers[layers$role == "cost", ]
  pa_row    <- layers[layers$role == "mask_locked_in", ]

  features <- terra::rast(abspath(feat_rows$path)); names(features) <- feat_rows$name
  cost     <- terra::rast(abspath(cost_row$path));  names(cost) <- "cost"
  pa       <- terra::rast(abspath(pa_row$path));    names(pa) <- "pa"

  # ---- ROI crop (+ optional polygon mask) -- the one new spatial op vs the monolith ----
  # bounds are grid-snapped in Python, so crop(snap="near") lands on integer cell boundaries.
  roi <- params$roi
  if (!is.null(roi$bounds)) {
    b   <- unlist(roi$bounds)                                 # [left, bottom, right, top]
    win <- terra::ext(b[1], b[3], b[2], b[4])                 # terra ext = xmin,xmax,ymin,ymax
    features <- terra::crop(features, win, snap = "near")
    cost     <- terra::crop(cost,     win, snap = "near")
    pa       <- terra::crop(pa,       win, snap = "near")
    if (!is.null(roi$mask_path)) {                            # ab_foothills: mask to the polygon
      roi_v    <- terra::vect(abspath(roi$mask_path))
      features <- terra::mask(features, roi_v)
      cost     <- terra::mask(cost,     roi_v)
      pa       <- terra::mask(pa,       roi_v)
    }
    cat(sprintf("ROI %s: cropped to %d x %d cells%s\n", roi$mode,
                terra::ncol(cost), terra::nrow(cost),
                if (is.null(roi$mask_path)) "" else " + polygon mask"))
  }

  # ---- Relaxed grid validation: sub-window CONTAINED in + ALIGNED to the manifest grid ----
  # (When roi.mode="full" this degenerates to the old full-grid equality check.)
  gb <- grid$bounds                                          # [left, bottom, right, top]
  res <- grid$res_m
  tol <- res * 0.01
  ref_dim <- c(terra::ncol(cost), terra::nrow(cost))         # every layer shares one crop
  chk <- function(r, nm, problems) {
    e <- unname(as.vector(terra::ext(r)))                    # xmin,xmax,ymin,ymax
    if (e[1] < gb[1] - tol || e[2] > gb[3] + tol || e[3] < gb[2] - tol || e[4] > gb[4] + tol)
      problems <- c(problems, sprintf("%s: extent outside the manifest grid", nm))
    da <- abs((e[1] - gb[1]) %% res); db <- abs((e[3] - gb[2]) %% res)
    if ((da > tol && da < res - tol) || (db > tol && db < res - tol))
      problems <- c(problems, sprintf("%s: not grid-aligned", nm))
    if (terra::ncol(r) != ref_dim[1] || terra::nrow(r) != ref_dim[2])
      problems <- c(problems, sprintf("%s: dims differ across layers", nm))
    problems
  }
  problems <- character(0)
  for (i in seq_len(terra::nlyr(features))) problems <- chk(features[[i]], names(features)[i], problems)
  problems <- chk(cost, "cost", problems); problems <- chk(pa, "pa", problems)
  if (length(problems)) stop("GRID VALIDATION FAILED:\n  ", paste(problems, collapse = "\n  "))
  cat(sprintf("ingested %d features (%d continuous + %d EFG) + cost + PA mask | grid %d x %d @ %d m\n",
              terra::nlyr(features), sum(is_cont), sum(is_efg),
              terra::ncol(cost), terra::nrow(cost), grid$res_m))

  # ---- Prototype coarsening (optional) -- crop THEN aggregate ----
  agg <- params$prototype_agg_factor
  if (agg > 1) {
    features <- terra::aggregate(features, agg, "mean", na.rm = TRUE)
    cost     <- terra::aggregate(cost,     agg, "mean", na.rm = TRUE)
    pa       <- terra::aggregate(pa,       agg, "mean", na.rm = TRUE)
    names(features) <- feat_rows$name; names(cost) <- "cost"; names(pa) <- "pa"
    cat(sprintf("PROTOTYPE: aggregated x%d -> %d x %d @ %d m (%s cells)\n",
                agg, terra::ncol(cost), terra::nrow(cost), grid$res_m * agg,
                format(terra::global(!is.na(cost), "sum", na.rm = TRUE)[[1]], big.mark = ",")))
  }

  # ---- Normalize each feature so its total = NORM_TOTAL (scale-invariant conditioning) ----
  fsum <- terra::global(features, "sum", na.rm = TRUE)[, 1]
  fsum[!is.finite(fsum) | fsum == 0] <- 1
  features <- features * (params$norm_total / fsum)
  names(features) <- feat_rows$name
  cat(sprintf("normalized %d features to total=%g each (scale-invariant conditioning)\n",
              terra::nlyr(features), params$norm_total))

  list(features = features, cost = cost, pa = pa,
       n_cont = sum(is_cont), n_efg = sum(is_efg),
       cell_m = grid$res_m * agg, feat_rows = feat_rows)
}

# ---- Stage 3: planning units + lock-in dispatch + feasibility ------------
pr_planning_units <- function(ctx) {
  params <- ctx$params; cost <- ctx$cost; pa <- ctx$pa; proj <- ctx$proj

  n_pu <- terra::global(!is.na(cost), "sum", na.rm = TRUE)[[1]]
  if (n_pu == 0)
    stop("ROI contains no planning-unit cells -- check the roi bounds / mask (empty crop).")
  total_cost <- terra::global(cost, "sum", na.rm = TRUE)[[1]]   # == n_pu (uniform cost)
  BUDGET <- params$budget_pct * total_cost                      # area budget in cost units

  # Lock-in source: existing PAs (pa_mask) or a rasterized polygon (vector, e.g. draft anchors).
  li <- params$lock_in
  if (identical(li$source, "vector")) {
    v <- terra::vect(file.path(proj, li$vector_path))            # already TARGET_CRS (Python)
    r <- terra::rasterize(v, cost, field = 1, background = 0)
    locked <- terra::mask(r >= 0.5, cost)
    li_desc <- sprintf("vector (%s)", basename(li$vector_path))
  } else {
    locked <- terra::mask(pa >= 0.5, cost)                       # PA lock-in mask (default)
    li_desc <- "pa_mask"
  }
  n_locked <- terra::global(locked, "sum", na.rm = TRUE)[[1]]

  cat(sprintf("planning units: %s cells | budget = %.0f%% = %s cells\n",
              format(n_pu, big.mark = ","), 100 * params$budget_pct, format(round(BUDGET), big.mark = ",")))
  cat(sprintf("locked-in [%s]: %s cells (%.1f%% of window) -- %s\n",
              li_desc, format(n_locked, big.mark = ","), 100 * n_locked / n_pu,
              if (n_locked <= BUDGET) "fits within budget" else "EXCEEDS BUDGET"))
  if (n_locked > BUDGET)
    stop("locked-in area exceeds the budget -> infeasible; raise budget_pct or reduce lock-in.")

  list(n_pu = n_pu, budget = BUDGET, locked = locked, n_locked = n_locked, total_cost = total_cost)
}

# ---- Stage 4: feature weights (+ per-analysis multipliers) ---------------
pr_weights <- function(ctx) {
  params <- ctx$params; features <- ctx$features; n_cont <- ctx$n_cont; n_efg <- ctx$n_efg
  # Each continuous feature @ 1.0; the EFG group shares a total of 1.0 (each EFG @ 1/n_efg).
  weights <- c(rep(1.0, n_cont), rep(1.0 / n_efg, n_efg))
  names(weights) <- names(features)
  cat(sprintf("weights: %d continuous @ 1.0 ; %d EFG @ %.4f (EFG group total = 1.0)\n",
              n_cont, n_efg, 1.0 / n_efg))
  # Per-analysis up-weighting (e.g. north_bc: connectivity + corridors x5). Name-keyed; fail
  # loud on an unknown feature name so a typo can't silently no-op.
  mult <- params$feature_weight_multipliers
  for (nm in names(mult)) {
    stopifnot("feature_weight_multipliers names a feature not in the stack" = nm %in% names(weights))
    weights[nm] <- weights[nm] * as.numeric(mult[[nm]])
    cat(sprintf("  up-weight %s x%.1f -> %.4f\n", nm, as.numeric(mult[[nm]]), weights[nm]))
  }
  list(weights = weights)
}

# ---- Stage 5: spatial-penalty matrices (each only if its penalty > 0) ----
pr_penalty_matrices <- function(ctx) {
  params <- ctx$params; cost <- ctx$cost; features <- ctx$features; cell_m <- ctx$cell_m
  cm <- NULL; bm <- NULL
  if (params$connectivity_penalty > 0) {
    cm <- prioritizr::connectivity_matrix(cost, features[["transboundary_connectivity"]])
    cat(sprintf("connectivity matrix: %s edges | weight range [%.4g, %.4g]\n",
                format(length(cm@x), big.mark = ","), min(cm@x), max(cm@x)))
  }
  if (params$boundary_penalty > 0) {
    bm <- prioritizr::boundary_matrix(cost)
    bm <- bm / cell_m                                          # metres -> edge units
    cat("boundary matrix built (edge units) for compactness penalty\n")
  }
  if (params$neighbor_penalty > 0)
    cat(sprintf("neighbor penalty ON (%g): binary rook adjacency derived from the PU raster\n",
                params$neighbor_penalty))
  cat(sprintf("penalties -> connectivity=%g | boundary=%g | neighbor=%g  (0 = off)\n",
              params$connectivity_penalty, params$boundary_penalty, params$neighbor_penalty))
  list(cm = cm, bm = bm)
}

# ---- Stage 6: build the conservation problem + drift-safe snapshot -------
pr_build_problem <- function(ctx) {
  params <- ctx$params; cost <- ctx$cost; features <- ctx$features
  weights <- ctx$weights; locked <- ctx$locked; budget <- ctx$budget
  cm <- ctx$cm; bm <- ctx$bm

  p <- problem(cost, features)
  if (identical(params$objective, "min_set")) {
    p <- p |> add_min_set_objective() |> add_relative_targets(params$target_pct)
  } else if (identical(params$objective, "max_utility")) {
    p <- p |> add_max_utility_objective(budget = budget) |> add_feature_weights(weights)
  } else {   # min_shortfall (default): maximise the captured fraction of every input
    p <- p |> add_min_shortfall_objective(budget = budget) |>
              add_relative_targets(params$target_pct) |> add_feature_weights(weights)
  }
  p <- p |> add_locked_in_constraints(locked)

  p <- if (identical(params$decision_type, "proportion")) p |> add_proportion_decisions()
       else p |> add_binary_decisions()

  # boundary and neighbor are alternative compactness drivers; connectivity is corridor-following.
  if (params$connectivity_penalty > 0) p <- p |> add_connectivity_penalties(params$connectivity_penalty, data = cm)
  if (params$boundary_penalty > 0)     p <- p |> add_boundary_penalties(params$boundary_penalty, data = bm)
  if (params$neighbor_penalty > 0)     p <- p |> add_neighbor_penalties(params$neighbor_penalty)

  n_threads <- parallel::detectCores()
  if (ctx$use_portfolio) {
    stopifnot("solver='gurobi' but the gurobi R package is not installed (see requirements-R.txt)" = ctx$have_gurobi)
    p <- p |>
      add_gap_portfolio(number_solutions = params$portfolio_n, pool_gap = params$portfolio_gap) |>
      add_gurobi_solver(gap = params$opt_gap, time_limit = params$solver_time_limit,
                        threads = n_threads, verbose = TRUE)
  } else {
    p <- p |> add_highs_solver(gap = params$opt_gap, time_limit = params$solver_time_limit,
                               threads = n_threads, verbose = TRUE,
                               control = list(solver = params$highs_solver))
  }
  print(p)

  # Snapshot the params ACTUALLY used to build this problem so run_summary records the TRUE
  # solve even if the manifest is refreshed before the write cell (drift guard).
  solve_params <- modifyList(params, list(
    connectivity_penalty = params$connectivity_penalty,
    boundary_penalty = params$boundary_penalty, neighbor_penalty = params$neighbor_penalty))
  list(p = p, solve_params = solve_params)
}

# ---- Stage 7: solve -----------------------------------------------------
pr_solve <- function(ctx) {
  timing <- system.time(s <- solve(ctx$p))
  n_sol <- terra::nlyr(s)
  names(s) <- sprintf("alt_%02d", seq_len(n_sol))
  cat(sprintf("solved with %s: %d solution(s) in %.1f s\n",
              ctx$params$solver, n_sol, timing[["elapsed"]]))
  list(s = s, timing = timing, n_sol = n_sol)
}

# ---- Stage 8: per-alternative summaries + selection-frequency map --------
pr_summaries <- function(ctx) {
  p <- ctx$p; s <- ctx$s; n_sol <- ctx$n_sol; locked <- ctx$locked; n_pu <- ctx$n_pu
  rep_rows <- list(); stat_rows <- list()
  for (i in seq_len(n_sol)) {
    sol <- s[[i]]
    fr <- eval_feature_representation_summary(p, sol)
    fr$alternative <- names(s)[i]
    rep_rows[[i]] <- fr
    n_sel <- terra::global(sol, "sum", na.rm = TRUE)[[1]]
    n_new <- terra::global(sol & (locked == 0), "sum", na.rm = TRUE)[[1]]
    stat_rows[[i]] <- data.frame(alternative = names(s)[i], n_selected = n_sel,
                                 pct_region = 100 * n_sel / n_pu, n_added_beyond_pa = n_new)
  }
  representation <- do.call(rbind, rep_rows)
  stats <- do.call(rbind, stat_rows)
  sel_freq <- sum(s); names(sel_freq) <- "selection_frequency"
  print(stats)
  list(representation = representation, stats = stats, sel_freq = sel_freq)
}

# ---- Stage 9: write outputs (drift-safe run_summary) --------------------
pr_write_outputs <- function(ctx) {
  params <- ctx$params; out_dir <- ctx$out_dir; s <- ctx$s; sel_freq <- ctx$sel_freq
  proj <- ctx$proj
  portfolio_tif <- file.path(out_dir, "portfolio.tif")
  freq_tif      <- file.path(out_dir, "selection_frequency.tif")
  rep_csv       <- file.path(out_dir, "portfolio_representation.csv")
  summary_json  <- file.path(out_dir, "run_summary.json")

  if (identical(params$decision_type, "proportion")) {
    terra::writeRaster(s, portfolio_tif, overwrite = TRUE, datatype = "FLT4S",
                       gdal = c("COMPRESS=DEFLATE", "TILED=YES"))
    terra::writeRaster(sel_freq, freq_tif, overwrite = TRUE, datatype = "FLT4S",
                       gdal = c("COMPRESS=DEFLATE", "TILED=YES"))
  } else {
    terra::writeRaster(s, portfolio_tif, overwrite = TRUE, datatype = "INT1U",
                       NAflag = 255, gdal = c("COMPRESS=DEFLATE", "TILED=YES"))
    terra::writeRaster(sel_freq, freq_tif, overwrite = TRUE, datatype = "INT1U",
                       NAflag = 255, gdal = c("COMPRESS=DEFLATE", "TILED=YES"))
  }
  write.csv(ctx$representation, rep_csv, row.names = FALSE)

  # Record the params ACTUALLY solved (snapshot from build), not the live manifest.
  solved_params <- if (!is.null(ctx$solve_params)) ctx$solve_params else params
  run_summary <- list(
    run_tag = ctx$run_tag, analysis = params$analysis, objective = params$objective,
    params = solved_params, n_planning_units = ctx$n_pu, budget_cells = round(ctx$budget),
    n_locked_in = ctx$n_locked, n_alternatives = ctx$n_sol,
    solve_seconds = unname(ctx$timing[["elapsed"]]), per_alternative = ctx$stats,
    versions = list(R = as.character(getRversion()),
                    prioritizr = as.character(packageVersion("prioritizr")),
                    terra = as.character(packageVersion("terra")),
                    gurobi = if (ctx$have_gurobi) as.character(packageVersion("gurobi")) else NA))
  jsonlite::write_json(run_summary, summary_json, auto_unbox = TRUE, pretty = TRUE, na = "null")

  cat("wrote:\n")
  for (f in c(portfolio_tif, freq_tif, rep_csv, summary_json))
    cat(sprintf("  %s\n", sub(paste0(proj, "/"), "", f)))
  invisible(list(portfolio = portfolio_tif, freq = freq_tif, rep = rep_csv, summary = summary_json))
}

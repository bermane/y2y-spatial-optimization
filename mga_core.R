# mga_core.R -- diversity-controlled near-optimal generation (spec v0.10, estimator
# `mga_maxham_v1`). The within-cell estimator that replaced the k-best pool after Gate 2
# measured that PoolSearchMode=2 never samples the g-band (M6.6): generate k maximally-
# diverse members of the band {x : objective(x) <= (1+g) * certified optimum} by iterative
# max-Hamming MGA (Brill 1979 lineage; Brunel et al. 2023 the direct parent).
#
# Mechanism: prioritizr cannot constrain its own objective, so we work on the COMPILED model
# (prioritizr::compile exposes R6 mutators). PU decision variables are columns 1..n_pu
# ("pu", binary; locked-in PAs are lb=1); shortfall variables ("spp_met") follow, carrying
# the feature weights in the objective. One appended row -- obj0 . x <= (1+g) * z* -- is the
# band wall; each iteration swaps the objective for a LINEAR max-sum-of-Hamming distance to
# the incumbents (minimize sum_j (2*count_j - n_inc) * x_j over DISCRETIONARY pu columns:
# never-selected cells get negative coefficients = rewarded, always-selected positive =
# deselection rewarded), which probes the band's extremes in both directions.
#
# Honest-certificate detail: the shortfall variables have no downward pressure once the
# distance objective replaces the original one (the band row only caps them), so a tiny
# +1e-3 * obj0 term is kept in every distance objective. That pins each shortfall variable
# to its true minimum for the chosen selection -- making band_lhs (= obj0 . x) the REAL
# objective value of the member, at a distance-objective distortion of <= ~6e-3 of one
# Hamming unit (integer-scaled), i.e. none.
#
# Direct gurobi::gurobi calls mirror prioritizr's own GurobiSolver construction (model list,
# LC_CTYPE="C" locale wrapper, binary rounding post-process, model$start warm starts);
# NumericFocus 2 engine standard applies (M5.3).

suppressPackageStartupMessages({
  library(Matrix)
})

# ---- compiled-model handle ----------------------------------------------
mga_compile <- function(ctx) {
  stopifnot("mga_compile needs ctx$p (run pr_build_problem first)" = !is.null(ctx$p))
  o <- prioritizr::compile(ctx$p)
  n_pu <- o$number_of_planning_units()
  ids <- o$col_ids()
  stopifnot("compiled layout unexpected: pu columns must come first" =
              identical(ids[seq_len(n_pu)], rep("pu", n_pu)))
  lb <- o$lb()
  locked <- lb[seq_len(n_pu)] >= 1 - 1e-9      # locked-in constraints are lb = 1
  cat(sprintf("compiled: %d cols (%d pu + %d aux) x %d rows | %d locked pu | modelsense %s\n",
              o$ncol(), n_pu, o$ncol() - n_pu, o$nrow(), sum(locked), o$modelsense()))
  list(o = o, n_pu = n_pu, obj0 = o$obj(), locked = locked,
       pu_index = ctx$p$planning_unit_indices())
}

# ---- gurobi plumbing (mirrors prioritizr's GurobiSolver) ----------------
mga_model <- function(o) {
  list(modelsense = o$modelsense(), vtype = o$vtype(), obj = o$obj(),
       A = o$A(), rhs = o$rhs(), sense = o$sense(), lb = o$lb(), ub = o$ub())
}

mga_gurobi <- function(model, mip_gap, time_limit, threads, verbose = FALSE) {
  params <- list(LogToConsole = as.numeric(verbose), LogFile = "", Presolve = 2,
                 MIPGap = mip_gap, TimeLimit = time_limit, Threads = threads,
                 NumericFocus = 2)
  res <- withr::with_locale(c(LC_CTYPE = "C"),
                            gurobi::gurobi(model = model, params = params))
  if (!is.null(res$x)) {              # prioritizr's post-process: round binaries, clamp
    b <- model$vtype == "B"
    res$x[b] <- round(res$x[b])
    res$x <- pmin(pmax(res$x, model$lb), model$ub)
  }
  res
}

# ---- the anchor: certified optimum of the ORIGINAL problem --------------
mga_anchor <- function(cm, opt_gap = 1e-4, time_limit = 43200,
                       threads = parallel::detectCores()) {
  t0 <- proc.time()[["elapsed"]]
  res <- mga_gurobi(mga_model(cm$o), opt_gap, time_limit, threads)
  stopifnot("anchor solve did not reach OPTIMAL" = identical(res$status, "OPTIMAL"))
  x <- res$x[seq_len(cm$n_pu)] > 0.5
  gap <- (res$objval - res$objbound) / max(abs(res$objval), 1e-12)
  cat(sprintf("anchor: objective %.6f (bound %.6f, gap %.2e) | %s selected | %.0f s\n",
              res$objval, res$objbound, gap,
              format(sum(x), big.mark = ","), proc.time()[["elapsed"]] - t0))
  list(x = x, z = res$objval, bound = res$objbound, gap = gap,
       runtime = res$runtime, x_full = res$x)
}

# ---- the generator: k maximally-diverse members of the g-band -----------
mga_generate <- function(cm, anchor, g, k, mip_gap_dist = 0.01, time_limit_iter = 900,
                         threads = parallel::detectCores()) {
  o <- cm$o$copy()                            # pristine cm$o survives for other g levels
  ncol_o <- o$ncol()
  band_rhs <- (1 + g) * anchor$z
  nz <- which(cm$obj0 != 0)
  A_band <- Matrix::sparseMatrix(i = rep(1L, length(nz)), j = nz, x = cm$obj0[nz],
                                 dims = c(1L, ncol_o))
  o$append_linear_constraints(rhs = band_rhs, sense = "<=", A = A_band,
                              row_ids = "mga_band")
  cat(sprintf("band wall appended: obj0 . x <= %.6f  (g = %g on z* = %.6f)\n",
              band_rhs, g, anchor$z))

  disc <- which(!cm$locked)                   # discretionary pu columns
  counts <- as.numeric(anchor$x)              # selections among incumbents (anchor included)
  n_inc <- 1L
  members <- matrix(FALSE, nrow = k, ncol = cm$n_pu)
  cert <- vector("list", k)
  prev_x_full <- anchor$x_full
  t_all <- proc.time()[["elapsed"]]

  for (i in seq_len(k)) {
    dist_obj <- numeric(ncol_o)
    dist_obj[disc] <- 2 * counts[disc] - n_inc      # minimize => maximize summed Hamming
    dist_obj[nz] <- dist_obj[nz] + 1e-3 * cm$obj0[nz]  # pin shortfalls to their true minimum
    o$set_obj(dist_obj)
    model <- mga_model(o)
    model$start <- prev_x_full                      # warm start from the previous member
    t0 <- proc.time()[["elapsed"]]
    res <- mga_gurobi(model, mip_gap_dist, time_limit_iter, threads)
    stopifnot("MGA iterate returned no solution (band infeasible?)" = !is.null(res$x))
    x <- res$x[seq_len(cm$n_pu)] > 0.5
    band_lhs <- sum(cm$obj0 * res$x)                # TRUE objective of this member (see header)
    dup <- if (i > 1) any(apply(members[seq_len(i - 1), , drop = FALSE], 1,
                                function(m) all(m == x))) else FALSE
    members[i, ] <- x
    counts <- counts + as.numeric(x)
    n_inc <- n_inc + 1L
    prev_x_full <- res$x
    el <- proc.time()[["elapsed"]] - t0
    cert[[i]] <- data.frame(
      iter = i, status = res$status, dist_objval = res$objval,
      band_lhs = band_lhs, band_rhs = band_rhs,
      band_ok = band_lhs <= band_rhs + 1e-6,
      pct_over_optimum = 100 * (band_lhs - anchor$z) / anchor$z,
      n_selected = sum(x), hamming_to_anchor = sum(x != anchor$x),
      duplicate = dup, mip_gap_used = mip_gap_dist, runtime_s = el)
    cat(sprintf("g=%g iter %02d/%d: band %.6f (%+.2f%% of z*) %s | ham(anchor) %s | %s%.0f s\n",
                g, i, k, band_lhs, cert[[i]]$pct_over_optimum,
                if (cert[[i]]$band_ok) "OK" else "VIOLATED",
                format(cert[[i]]$hamming_to_anchor, big.mark = ","),
                if (dup) "DUPLICATE | " else "", el))
  }
  cat(sprintf("g=%g: %d members in %.1f min (%d duplicates, %d time-limited)\n",
              g, k, (proc.time()[["elapsed"]] - t_all) / 60,
              sum(sapply(cert, function(d) d$duplicate)),
              sum(sapply(cert, function(d) d$status == "TIME_LIMIT"))))
  list(members = members, certificates = do.call(rbind, cert),
       band_rhs = band_rhs, g = g, k = k)
}

# ---- raster writer: members matrix -> k-band INT1U GeoTIFF --------------
mga_write <- function(gen, cm, template, out_dir, tag) {
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  layers <- lapply(seq_len(gen$k), function(i) {
    r <- terra::rast(template)                 # geometry only, values empty
    v <- rep(NA_integer_, terra::ncell(r))
    v[cm$pu_index] <- as.integer(gen$members[i, ])
    terra::values(r) <- v
    r
  })
  s <- terra::rast(layers)
  names(s) <- sprintf("mga_%02d", seq_len(gen$k))
  tif <- file.path(out_dir, sprintf("mga_%s.tif", tag))
  terra::writeRaster(s, tif, overwrite = TRUE, datatype = "INT1U", NAflag = 255,
                     gdal = c("COMPRESS=DEFLATE", "TILED=YES"))
  csv <- file.path(out_dir, sprintf("certificates_%s.csv", tag))
  write.csv(gen$certificates, csv, row.names = FALSE)
  cat(sprintf("wrote %s + %s\n", tif, csv))
  invisible(list(tif = tif, csv = csv))
}

#!/usr/bin/env Rscript
# run_one.R -- headless single-solve driver for the ensemble runner (Phase 2).
#
#   Rscript run_one.R <manifest_path> <project_dir>
#
# Mirrors 03a/03b/03c cells 1-9 EXACTLY, with one difference: it takes the manifest path as an
# argument and calls pr_setup() directly, instead of pr_refresh_manifest() (which regenerates the
# canonical aligned_stack/manifest.json from config.py). The ensemble needs per-run manifests --
# concurrent runs must not share one file, and each run's params are a patched copy, not whatever
# config.py currently says. pr_setup() already accepts a path, so the engine needs no change.
#
# This script holds NO logic of its own. If it ever diverges from the notebook flow, that is a
# bug: the whole point is that an ensemble run and a notebook run solve the identical problem.
# Everything (objective, penalties, weights, budget, ROI, output dir) comes from the manifest.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2)
  stop("usage: Rscript run_one.R <manifest_path> <project_dir>")

MANIFEST <- args[[1]]
PROJ     <- normalizePath(args[[2]])
stopifnot("manifest not found" = file.exists(MANIFEST))

setwd(PROJ)                                  # pr_* resolve layer paths relative to the project
source(file.path(PROJ, "prioritizr_core.R"))

ctx <- pr_setup(MANIFEST, PROJ)
ctx <- modifyList(ctx, pr_ingest(ctx))
ctx <- modifyList(ctx, pr_planning_units(ctx))
ctx <- modifyList(ctx, pr_weights(ctx))
ctx <- modifyList(ctx, pr_penalty_matrices(ctx))

bp  <- pr_build_problem(ctx); ctx$p <- bp$p; ctx$solve_params <- bp$solve_params
sv  <- pr_solve(ctx); ctx$s <- sv$s; ctx$timing <- sv$timing; ctx$n_sol <- sv$n_sol

ctx <- modifyList(ctx, pr_summaries(ctx))
pr_write_outputs(ctx)

cat("RUN_ONE_OK\n")                          # sentinel the Python runner greps for

#!/bin/bash
python run_evaluation.py \
    --predictions_path "/home/svz5418/shaokun/SWE-bench/inference/outputs/gpt-4-1106-preview__SWE-bench_oracle__test.jsonl" \
    --swe_bench_tasks "/home/svz5418/shaokun/SWE-bench/harness/swe-bench.json" \
    --log_dir "/home/svz5418/shaokun/SWE-bench/inference/outputs/log/" \
    --testbed "/home/svz5418/shaokun/SWE-bench/inference/outputs/testbed/" \
    --skip_existing \
    --timeout 900 \
    --verbose

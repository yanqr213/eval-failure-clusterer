import json
import unittest

from eval_failure_clusterer.analyzer import analyze_records
from eval_failure_clusterer.baseline import render_reviewed_baseline, split_reviewed_clusters
from eval_failure_clusterer.checks import collect_check_issues
from eval_failure_clusterer.compare import compare_analysis
from eval_failure_clusterer.config import load_config
from eval_failure_clusterer.parser import load_records


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.result = analyze_records(load_records("examples/eval_results.jsonl", self.config), self.config)
        baseline = analyze_records(load_records("examples/baseline_eval.jsonl", self.config), self.config)
        self.compare = compare_analysis(baseline, self.result)

    def test_collect_check_issues_for_analysis(self):
        issues = collect_check_issues(self.result)
        self.assertTrue(any("failed records" in issue for issue in issues))

    def test_collect_check_issues_with_compare(self):
        issues = collect_check_issues(self.result, self.compare)
        self.assertTrue(any("regressed" in issue or "new failure modes" in issue for issue in issues))

    def test_reviewed_clusters_do_not_trigger_failed_record_issue(self):
        baseline = render_reviewed_baseline(self.result)
        keys = {item["cluster_key"] for item in json.loads(baseline)["clusters"]}
        split = split_reviewed_clusters(self.result, keys)

        issues = collect_check_issues(self.result, open_clusters=split["open"])

        self.assertFalse(any("failed records" in issue for issue in issues))

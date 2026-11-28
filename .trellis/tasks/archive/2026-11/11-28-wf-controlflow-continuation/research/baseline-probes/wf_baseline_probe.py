import sys, json
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
from wflib import check, runs, projection

STEP = {
  "id": "build", "type": "task",
  "actions": [
    {"id": "write", "required": True, "skip": None,
     "human_points": [{"id": "approve-write", "question": "ok?", "choices": ["yes","no"]}]},
  ],
  "human_points": [{"id": "confirm", "question": "accept?", "choices": ["yes","no"]}],
  "verifications": [{"id": "v1", "source": "current_plan", "consume_at": "finish",
                     "stored_in": {"kind": "task_plan", "verification_id": "v1"}}],
}
contract = runs.step_contract({"steps":[STEP]}, STEP, run_id="r1",
                              run={"definition":{"digest":"sha256:"+"a"*64}}, workflow_id="wf-demo")
print("contract.verifications:", json.dumps(contract["verifications"], ensure_ascii=False))
plan = {"verifications":[{"id":"v1","consume_at":"check"}]}
task = {"id":"t1","plan":plan,"execution":contract}

def run(name, decisions):
    c = check.check_step_contract(type("C",(),{"root":"."})(), task, plan, decisions)
    print(name, "problems=", [p["kind"] for p in c["problems"]], "results=", c["applied"])

run("waived-on-required-no-skip", [{"subject":"write","choice":"waived"},{"subject":"confirm","choice":"yes"}])
run("invalid-human-choice", [{"subject":"write","choice":"done"},{"subject":"confirm","choice":"maybe"}])
run("unanswered-action-human-point", [{"subject":"write","choice":"done"},{"subject":"confirm","choice":"yes"}])
run("verification-consume-at-mismatch", [{"subject":"write","choice":"done"},{"subject":"confirm","choice":"yes"}])

# verify resolve: nonexistent acceptance id
task2 = {"id":"t2","plan":{"acceptance":[{"id":"a1"}]},"check":{"acceptance_results":[{"acceptance_id":"a1","conclusion":"unverified"}]}}
rec, problems = projection.resolve(task2, "a-does-not-exist", kind="narrow", evidence="e",
                                   reason="r", impact="i", compensation="c")
print("verify-resolve-nonexistent:", "accepted" if rec else "rejected", problems)

# check publish vs consume: basis missing
import tempfile, os
fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd)
json.dump({"standard":{"conclusion":"pass"},"requirement":{"conclusion":"pass"}}, open(path,"w"))
review, problem = check._parse_review_notes(path)
print("parse-pass-without-basis:", "accepted" if review else "rejected", problem)
check_rec = {"result":"pass","anchor":{"rule_version":"x"},"commands":[],"acceptance_results":[],"internal_review":review}
print("validate_check_result problems:", check.validate_check_result({"plan":{"verifications":[],"acceptance":[]}}, check_rec))
os.unlink(path)

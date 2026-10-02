from voiceinput.engine.context import AsrResult
from voiceinput.engine.pipeline import Pipeline


def test_reload_and_last_good(store, root):
    pipe = Pipeline(store)
    path = root / "lua/user/custom.lua"
    path.write_text('function filter(ctx) ctx.text = ctx.text .. "OK"; return ctx end', encoding="utf-8")
    assert pipe.process(AsrResult("测试"), "science").text.endswith("OK")
    path.write_text('function ???', encoding="utf-8")
    ctx = pipe.process(AsrResult("测试"), "science")
    assert ctx.text.endswith("OK") and ctx.metadata["errors"]


def test_sandbox_and_instruction_limit(store, root):
    path = root / "lua/user/custom.lua"
    path.write_text('function filter(ctx) assert(os == nil and io == nil and python == nil and require == nil); return ctx end', encoding="utf-8")
    pipe = Pipeline(store)
    assert not pipe.process(AsrResult("测试"), "normal").metadata.get("errors")
    path.write_text('function filter(ctx) while true do end end', encoding="utf-8")
    assert pipe.process(AsrResult("测试"), "normal").metadata["errors"]


def test_config_readonly_and_notes(store, root):
    path = root / "lua/user/custom.lua"
    path.write_text('function filter(ctx) ctx.trace[1]="checked"; ctx.metadata.custom="yes"; assert(ctx.config.audio.sample_rate == 16000); return ctx end', encoding="utf-8")
    ctx = Pipeline(store).process(AsrResult("测试"), "normal")
    assert ctx.metadata["custom"] == "yes"
    assert any(e.details.get("notes") for e in ctx.trace)
    path.write_text('function filter(ctx) ctx.config.audio.sample_rate=8000; return ctx end', encoding="utf-8")
    ctx = Pipeline(store).process(AsrResult("测试"), "normal")
    assert ctx.metadata["errors"]
    assert store.data["audio"]["sample_rate"] == 16000

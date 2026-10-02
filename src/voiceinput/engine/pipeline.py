from voiceinput.engine.context import TextContext, TraceEvent
from voiceinput.engine.normalizers import number_normalizer, unit_normalizer, punctuation_filter
from voiceinput.lua.runtime import LuaFilters
import re


class Pipeline:
    def __init__(self, store):
        self.store = store
        self.lua = LuaFilters(store.root / "lua")

    def process(self, result, profile, app_name=None):
        ctx = TextContext(result.text, result.text, profile, app_name, result.language, metadata=dict(result.metadata))
        ctx.trace.append(TraceEvent("asr", "sensevoice", "", result.text))
        settings = self.store.data["profiles"][profile]
        for stage in ("processors", "translators", "filters"):
            for component in self.store.data["engine"][stage]:
                if component in settings.get("disabled", []) or ("only" in settings and component not in settings["only"]):
                    continue
                before = ctx.text
                if component in ("correction_dictionary", "terminology_dictionary", "chemistry_normalizer"):
                    names = ["user"] if component == "correction_dictionary" else settings.get("dictionaries", [])
                    if component == "terminology_dictionary":
                        names = [n for n in names if n != "chemistry"]
                    elif component == "chemistry_normalizer":
                        names = [n for n in names if n == "chemistry"]
                    replacements = {}
                    for name in names:
                        dictionary = self.store.dictionaries.get(name, {})
                        for rule in dictionary.get("corrections", []) + dictionary.get("terms", []):
                            if rule.get("profiles") and profile not in rule["profiles"]:
                                continue
                            for spoken in rule.get("spoken", [rule.get("from")]):
                                replacements.setdefault(spoken, (rule.get("output", rule.get("to")), rule.get("id"), name))
                    if replacements:
                        pattern = "|".join(re.escape(x) for x in sorted(replacements, key=len, reverse=True))
                        matched = []
                        def replace(m):
                            output, rule, name = replacements[m[0]]
                            matched.append((rule, name))
                            return output
                        ctx.text = re.sub(pattern, replace, ctx.text)
                        for rule, name in matched:
                            ctx.trace.append(TraceEvent(stage, component, before, ctx.text, rule, f"dictionaries/{name}.yaml"))
                elif component.startswith("lua:") and self.store.data["lua"]["enabled"]:
                    ctx.text, error = self.lua.run(component[4:], ctx, self.store.data["lua"].get("hot_reload", True), self.store.data)
                    if error:
                        ctx.metadata.setdefault("errors", []).append(f"{component}: {error}")
                elif component == "number_normalizer":
                    ctx.text = number_normalizer(ctx.text)
                elif component == "unit_normalizer":
                    ctx.text = unit_normalizer(ctx.text)
                elif component == "punctuation_filter":
                    ctx.text = punctuation_filter(ctx.text)
                elif component == "final_cleanup":
                    ctx.text = ctx.text.strip()
                notes = ctx.metadata.get("lua_notes", {}).get(component[4:], {}) if component.startswith("lua:") else {}
                ctx.trace.append(TraceEvent(stage, component, before, ctx.text, details={"notes": notes} if notes else {}))
        return ctx

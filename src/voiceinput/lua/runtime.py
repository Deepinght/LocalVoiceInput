from pathlib import Path
from lupa import LuaRuntime


class LuaFilters:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.cache = {}

    def compile(self, source):
        lua = LuaRuntime(register_eval=False, register_builtins=False, max_memory=8 * 1024 * 1024)
        # Only Lua values cross the boundary; the environment has no Python, IO or loader.
        factory = lua.eval('''function(source)
          local env = {string=string, math=math, table=table, utf8=utf8,
            pairs=pairs, ipairs=ipairs, tostring=tostring, tonumber=tonumber,
            type=type, assert=assert, error=error, select=select}
          local fn, err = load(source, "filter", "t", env)
          if not fn then error(err) end
          local function limited(call, arg)
            local count=0
            debug.sethook(function() count=count+1; if count>100 then error("Lua instruction limit") end end,"",1000)
            local ok, result=pcall(call,arg)
            debug.sethook()
            if not ok then error(result) end
            return result
          end
          limited(fn)
          if type(env.filter)~="function" then error("missing filter(ctx)") end
          return function(ctx) return limited(env.filter,ctx) end
        end''')
        return lua, factory(source)

    def run(self, name, context, reload=True, config=None):
        path = (self.root / (name + ".lua")).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Lua 路径越界")
        error = None
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            if name not in self.cache:
                return context.text, str(exc)
            source = self.cache[name][0]
            error = str(exc)
        if name not in self.cache or (reload and self.cache[name][0] != source):
            try:
                lua, fn = self.compile(source)
                self.cache[name] = (source, lua, fn)
            except Exception as exc:
                error = str(exc)
                if name not in self.cache:
                    return context.text, error
        _, lua, fn = self.cache[name]
        ctx = lua.table_from({"text": context.text, "raw_text": context.raw_text, "profile": context.profile, "app_name": context.app_name or "", "language": context.language or "", "metadata": context.metadata, "trace": {}}, recursive=True)
        readonly = lua.eval('''function(value)
          local function freeze(t)
            if type(t) ~= "table" then return t end
            local copy = {}; for k,v in pairs(t) do copy[k]=freeze(v) end
            return setmetatable({}, {__index=copy, __newindex=function() error("configuration is read-only") end, __pairs=function() return next,copy,nil end, __metatable=false})
          end
          return freeze(value)
        end''')
        ctx["config"] = readonly(lua.table_from(config or {}, recursive=True))
        try:
            result = fn(ctx)
            text = result["text"]
            if not isinstance(text, str) or len(text) > 100000:
                raise ValueError("Lua 返回的文本无效或过长")
            def plain(value, depth=0):
                if depth > 6:
                    return "[depth limit]"
                if value is None or isinstance(value, (str, float, int, bool)):
                    return value
                if hasattr(value, "items"):
                    return {str(k): plain(v, depth+1) for k,v in list(value.items())[:100]}
                return str(value)
            notes = plain(result["trace"])
            if notes:
                context.metadata.setdefault("lua_notes", {})[name] = notes
            additions = plain(result["metadata"])
            if isinstance(additions, dict):
                # Keep engine-owned errors/notes intact.
                for key, value in additions.items():
                    if key not in ("errors", "lua_notes"):
                        context.metadata[key] = value
            return text, error
        except Exception as exc:
            return context.text, str(exc)

function filter(ctx)
  ctx.text = ctx.text:gsub('(Nm³/h)(温度)', '%1，%2')
  ctx.text = ctx.text:gsub('(流量)(%d)', '%1为%2'):gsub('(温度)(%d)', '%1为%2')
  return ctx
end

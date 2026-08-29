### `--reload` 是什么意思？

`reload` 的意思就是：

> **重新加载。**

`--reload` 开启后，Uvicorn 会监视你的代码。

例如服务器正在运行：

```
python -m uvicorn app.main:app --reload
```

然后你修改：

```
return {"message": "hello"}
```

变成：

```
return {"message": "hello world"}
```

保存文件以后，不需要你手动：

```
Ctrl + C
重新运行 uvicorn
```

Uvicorn 会自动检测：

```
代码发生变化
↓
自动重启服务器
↓
加载新代码
```

所以开发 FastAPI 项目时通常都会加：

```
--reload
```

不过它主要适合**开发环境**，正式部署一般不会使用它
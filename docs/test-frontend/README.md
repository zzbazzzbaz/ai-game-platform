启动：npm install 后执行 npm run dev，浏览器打开 http://localhost:3000。
环境变量：NEXT_PUBLIC_BACKEND_URL 业务接口地址（默认 http://127.0.0.1:8000），NEXT_PUBLIC_LANGGRAPH_URL 对话服务地址（默认 http://localhost:2024），NEXT_PUBLIC_ASSISTANT_ID 助手标识（默认 agent）。
联调顺序：顶部登录拿令牌后点新会话，再左侧对话、遇审批卡点批准或修改，最后右侧发布并选版本试玩。

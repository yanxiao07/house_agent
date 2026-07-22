const apiUrl = import.meta.env.VITE_LANGGRAPH_API_URL?.replace(/\/$/, '')
const assistantId = import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID || 'house_agent'

function getLastMessage(state) {
  const message = state?.messages?.at(-1)
  return typeof message?.content === 'string' ? message.content : ''
}

function parseStream(body) {
  let latestState = {}
  let interrupt = ''
  for (const event of body.split(/\r?\n\r?\n/)) {
    const payload = event.match(/^data:\s*(.+)$/m)?.[1]?.trim()
    if (!payload) continue
    try {
      const data = JSON.parse(payload)
      if (/^event:\s*values\s*$/m.test(event)) latestState = data
      if (/^event:\s*updates\s*$/m.test(event)) {
        interrupt = data.__interrupt__?.[0]?.value || interrupt
      }
    } catch {
      // Ignore malformed keepalive packets and retain the latest complete state.
    }
  }
  return { state: latestState, interrupt }
}

async function createThread() {
  const response = await fetch(`${apiUrl}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  if (!response.ok) throw new Error(`无法创建会话 (${response.status})`)
  const data = await response.json()
  if (!data.thread_id) throw new Error('服务未返回会话标识')
  return data.thread_id
}

export async function askAgent(content, threadId, resume = false) {
  if (!apiUrl) {
    throw new Error('租赁服务未连接，请配置 VITE_LANGGRAPH_API_URL')
  }

  const thread = threadId || await createThread()
  const response = await fetch(`${apiUrl}/threads/${thread}/runs/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assistant_id: assistantId,
      ...(resume ? { command: { resume: content } } : { input: { messages: [{ type: 'human', content }] } }),
      stream_mode: 'values',
      config: { configurable: { user_id: 'web-demo-user' } },
    }),
  })
  if (!response.ok) throw new Error(`租赁服务不可用 (${response.status})`)

  const { state, interrupt } = parseStream(await response.text())
  const message = interrupt || getLastMessage(state)
  if (!message) throw new Error('服务未返回有效响应')
  return { content: message, threadId: thread, state, interrupted: Boolean(interrupt) }
}

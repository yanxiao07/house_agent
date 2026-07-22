const apiUrl = import.meta.env.VITE_LANGGRAPH_API_URL?.replace(/\/$/, '')
const assistantId = import.meta.env.VITE_LANGGRAPH_ASSISTANT_ID || 'house_agent'

const demoResponses = [
  '根据你的预算和通勤需求，建议优先查看地铁 10 分钟内、采光朝南的房源。我已把相符的房源置顶。',
  '可以的。我会先核验房源档期，再为你发起看房预约。请在右侧卡片中选择合适的时段。',
  '已记录你的偏好。后续推荐会优先考虑通勤效率、预算和居住安静度。',
]

function getText(event) {
  if (typeof event === 'string') return event
  if (event?.data && typeof event.data === 'string') return event.data
  const messages = event?.data?.messages || event?.messages
  const lastMessage = messages?.[messages.length - 1]
  return typeof lastMessage?.content === 'string' ? lastMessage.content : ''
}

export async function askAgent(content, threadId) {
  if (!apiUrl) {
    await new Promise((resolve) => window.setTimeout(resolve, 550))
    return { content: demoResponses.find((item) => content.includes('预约')) || demoResponses[0], threadId }
  }

  let thread = threadId
  if (!thread) {
    const threadResponse = await fetch(`${apiUrl}/threads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    })
    if (!threadResponse.ok) throw new Error(`无法创建会话 (${threadResponse.status})`)
    const threadData = await threadResponse.json()
    thread = threadData.thread_id
    if (!thread) throw new Error('服务未返回会话标识')
  }
  const response = await fetch(`${apiUrl}/threads/${thread}/runs/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assistant_id: assistantId,
      input: { messages: [{ type: 'human', content }] },
      stream_mode: 'values',
      config: { configurable: { user_id: 'web-demo-user' } },
    }),
  })

  if (!response.ok) throw new Error(`服务暂不可用 (${response.status})`)

  const body = await response.text()
  const message = body
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim())
    .filter((payload) => payload && payload !== '[DONE]')
    .map((payload) => {
      try {
        return getText(JSON.parse(payload))
      } catch {
        return ''
      }
    })
    .filter(Boolean)
    .at(-1)

  return { content: message || '已收到你的需求，正在为你整理匹配结果。', threadId: thread }
}

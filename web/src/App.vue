<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { gsap } from 'gsap'
import {
  ArrowRight, ChatDotRound, CloseBold, CollectionTag, Document, House, Location, Message, Plus, RefreshRight, Search, Setting, Star, Tickets, UserFilled,
} from '@element-plus/icons-vue'
import HouseScene from './components/HouseScene.vue'
import { askAgent } from './services/agent'
import { cancelPersistedBooking, loadConversation, persistBooking, recordConversation } from './services/gateway'

function getBrowserId(key, prefix) {
  const stored = window.localStorage.getItem(key)
  if (stored) return stored
  const value = `${prefix}-${window.crypto.randomUUID()}`
  window.localStorage.setItem(key, value)
  return value
}

const appRoot = ref(null)
const activeView = ref('finder')
const city = ref('上海')
const districts = ref([])
const budget = ref([3000, 9500])
const keyword = ref('')
const activeSort = ref('recommend')
const chatInput = ref('')
const chatLoading = ref(false)
const tenantId = getBrowserId('house-agent-user-id', 'tenant')
const threadId = ref(window.localStorage.getItem('house-agent-thread-id') || '')
const pendingInterrupt = ref(false)
const chatScroll = ref(null)
const selectedHouse = ref(null)
const bookingDialog = ref(false)
const bookingSaving = ref(false)
const bookingConfirmed = ref(false)
const bookingForm = ref({ time: '', phone: '', idCard: '' })
const reservedHouseIds = ref([])
const appointmentPhone = ref(window.localStorage.getItem('house-agent-phone') || '')
const appointments = ref([])
const appointmentsLoading = ref(false)
const appointmentsError = ref('')
const contractText = ref('')
const contractLoading = ref(false)
const contractAnalysis = ref(null)
const contractError = ref('')
const houses = ref([])
const messages = ref([])
const imageFailures = ref(new Set())

let animationContext

const cityOptions = computed(() => [...new Set(houses.value.map((house) => house.city).filter(Boolean))].sort())
const districtOptions = computed(() => [...new Set(houses.value.filter((house) => !city.value || house.city === city.value).map((house) => house.district).filter(Boolean))].sort())
const sortedHouses = computed(() => {
  const sorted = [...houses.value]
  if (activeSort.value === 'latest') sorted.sort((left, right) => Number(right.id) - Number(left.id))
  if (activeSort.value === 'price') sorted.sort((left, right) => Number(left.price) - Number(right.price))
  if (activeSort.value === 'recommend') sorted.sort((left, right) => Number(right.score || 0) - Number(left.score || 0))
  return sorted.sort((left, right) => Number(reservedHouseIds.value.includes(String(right.id))) - Number(reservedHouseIds.value.includes(String(left.id))))
})

watch(city, () => { districts.value = districts.value.filter((district) => districtOptions.value.includes(district)) })
watch(activeView, async () => {
  await nextTick()
  if (!appRoot.value || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  gsap.fromTo('.view-surface', { autoAlpha: 0, y: 10 }, { autoAlpha: 1, y: 0, duration: 0.32, ease: 'power2.out' })
})

function applyAgentResponse(response) {
  threadId.value = response.threadId || threadId.value
  if (threadId.value) window.localStorage.setItem('house-agent-thread-id', threadId.value)
  if (Array.isArray(response.state.listings)) houses.value = response.state.listings
  pendingInterrupt.value = response.interrupted
  if (response.content) {
    const content = formatAssistantContent(response.content)
    markReservedListing(content)
    messages.value.push({ role: 'assistant', content })
  }
}

function persistTurn(role, content) {
  // Gateway persistence is optional; an unavailable REST service must not block the agent experience.
  recordConversation(tenantId, threadId.value, role, content).catch(() => {})
}

async function restoreConversation() {
  if (!threadId.value) return
  try {
    const history = await loadConversation(tenantId, threadId.value)
    if (history.length) messages.value = history.map((item) => ({ role: item.role, content: item.content }))
  } catch {
    // The active LangGraph thread and current session remain functional without the optional gateway.
  }
}

function markReservedListing(content) {
  if (!/(成功预约|预约工单已生成|工单号)/.test(content)) return
  const matched = houses.value.find((house) => content.includes(house.title))
  if (matched) reservedHouseIds.value = [...new Set([...reservedHouseIds.value, String(matched.id)])]
}

function formatAssistantContent(content) {
  return content
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/gm, '')
    .replace(/^\|\s*(.*?)\s*\|$/gm, (_, row) => row.split('|').map((cell) => cell.trim()).filter(Boolean).join('  '))
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function formatAppointmentTime(value) {
  if (!value) return '待顾问确认'
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function roomLabel(value) {
  return { one: '一居', two: '两居', three: '三居', studio: '开间' }[value] || value || '户型待确认'
}

function imageFailed(house) {
  imageFailures.value = new Set([...imageFailures.value, String(house.id)])
}

async function loadCatalog() {
  try {
    const response = await askAgent('', '', false, 'browse_agent')
    if (Array.isArray(response.state.listings)) {
      houses.value = response.state.listings
      if (!cityOptions.value.includes(city.value)) city.value = cityOptions.value[0] || ''
    }
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `房源初始化失败：${error.message}`, error: true })
  }
}

async function runSearch() {
  if (chatLoading.value) return
  const districtText = districts.value.length ? `，区域 ${districts.value.join('、')}` : ''
  const keywordText = keyword.value ? `，关键词 ${keyword.value}` : ''
  const content = `找房：${city.value || '不限城市'}${districtText}，预算 ${budget.value[0]} 到 ${budget.value[1]} 元/月${keywordText}`
  messages.value.push({ role: 'user', content })
  chatLoading.value = true
  try {
    const response = await askAgent(content, threadId.value, pendingInterrupt.value)
    applyAgentResponse(response)
    persistTurn('user', content)
    persistTurn('assistant', formatAssistantContent(response.content))
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `后端请求失败：${error.message}`, error: true })
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

function selectSuggestion(text) {
  chatInput.value = text
  sendMessage()
}

async function sendMessage() {
  const content = chatInput.value.trim()
  if (!content || chatLoading.value) return
  messages.value.push({ role: 'user', content })
  chatInput.value = ''
  chatLoading.value = true
  await scrollToBottom()
  try {
    const response = await askAgent(content, threadId.value, pendingInterrupt.value)
    applyAgentResponse(response)
    persistTurn('user', content)
    persistTurn('assistant', formatAssistantContent(response.content))
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `抱歉，${error.message}。请稍后重试。`, error: true })
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatScroll.value) chatScroll.value.setScrollTop(chatScroll.value.wrapRef.scrollHeight, 220)
}

function startNewConversation() {
  if (chatLoading.value) return
  threadId.value = ''
  pendingInterrupt.value = false
  chatInput.value = ''
  messages.value = []
  window.localStorage.removeItem('house-agent-thread-id')
}

function openBooking(house) {
  selectedHouse.value = house
  bookingForm.value = { time: '', phone: appointmentPhone.value, idCard: '' }
  bookingConfirmed.value = false
  bookingDialog.value = true
}

async function submitBooking() {
  if (!bookingForm.value.phone || !bookingForm.value.idCard || bookingSaving.value) return
  bookingSaving.value = true
  try {
    let response = await askAgent('', '', false, 'reserve_agent')
    response = await askAgent(selectedHouse.value.title, response.threadId, true, 'reserve_agent')
    response = await askAgent(bookingForm.value.phone, response.threadId, true, 'reserve_agent')
    response = await askAgent(bookingForm.value.idCard, response.threadId, true, 'reserve_agent')
    messages.value.push({ role: 'assistant', content: formatAssistantContent(response.content) })
    reservedHouseIds.value = [...new Set([...reservedHouseIds.value, String(selectedHouse.value.id)])]
    appointmentPhone.value = bookingForm.value.phone.trim()
    window.localStorage.setItem('house-agent-phone', appointmentPhone.value)
    const orderId = response.content.match(/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}/i)?.[0]
    if (orderId) {
      await syncAppointment(orderId)
      persistBooking({
        order_id: orderId, user_id: tenantId, house_id: String(selectedHouse.value.id), house_title: selectedHouse.value.title,
        phone_number: appointmentPhone.value, viewing_time: bookingForm.value.time ? new Date(bookingForm.value.time).toISOString() : null, status: 'confirmed',
      }).catch(() => {})
    }
    bookingConfirmed.value = true
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `预约提交失败：${error.message}`, error: true })
  } finally {
    bookingSaving.value = false
    await scrollToBottom()
  }
}

async function loadAppointments() {
  const phoneNumber = appointmentPhone.value.trim()
  if (!phoneNumber || appointmentsLoading.value) return
  appointmentsLoading.value = true
  appointmentsError.value = ''
  try {
    window.localStorage.setItem('house-agent-phone', phoneNumber)
    const response = await askAgent(JSON.stringify({ action: 'read', phone_number: phoneNumber }), '', false, 'appointments_agent')
    appointments.value = response.state.appointments || []
  } catch (error) {
    appointmentsError.value = `预约记录加载失败：${error.message}`
  } finally {
    appointmentsLoading.value = false
  }
}

async function syncAppointment(orderId) {
  const response = await askAgent(JSON.stringify({
    action: 'enrich', order_id: orderId, phone_number: appointmentPhone.value,
    viewing_time: bookingForm.value.time ? new Date(bookingForm.value.time).toISOString() : '',
  }), '', false, 'appointments_agent')
  appointments.value = response.state.appointments || []
}

async function cancelAppointment(appointment) {
  if (!window.confirm(`确认取消“${appointment.title}”的预约吗？`)) return
  appointmentsLoading.value = true
  try {
    const response = await askAgent(JSON.stringify({ action: 'cancel', order_id: appointment.order_id, phone_number: appointmentPhone.value }), '', false, 'appointments_agent')
    appointments.value = response.state.appointments || []
    cancelPersistedBooking(tenantId, appointment.order_id).catch(() => {})
  } catch (error) {
    appointmentsError.value = `预约取消失败：${error.message}`
  } finally {
    appointmentsLoading.value = false
  }
}

async function analyzeContract() {
  const text = contractText.value.trim()
  if (text.length < 20 || contractLoading.value) return
  contractLoading.value = true
  contractError.value = ''
  try {
    const response = await askAgent(text, '', false, 'contracts_agent')
    contractAnalysis.value = response.state.contract_analysis || null
  } catch (error) {
    contractError.value = `合同分析失败：${error.message}`
  } finally {
    contractLoading.value = false
  }
}

onMounted(() => {
  animationContext = gsap.context(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    gsap.from('.workspace-nav, .view-surface', { autoAlpha: 0, y: 12, duration: 0.42, stagger: 0.06, ease: 'power2.out' })
  }, appRoot.value)
  loadCatalog()
  loadAppointments()
  restoreConversation()
})

onUnmounted(() => animationContext?.revert())
</script>

<template>
  <main ref="appRoot" class="app-shell rental-workspace">
    <header class="topbar">
      <a class="brand" href="#finder" @click.prevent="activeView = 'finder'"><span class="brand-mark"><House /></span><span>住好家</span></a>
      <nav class="main-nav workspace-nav" aria-label="主导航">
        <button :class="{ active: activeView === 'finder' }" @click="activeView = 'finder'">找房工作台</button>
        <button :class="{ active: activeView === 'bookings' }" @click="activeView = 'bookings'">我的预约</button>
        <button :class="{ active: activeView === 'contracts' }" @click="activeView = 'contracts'">合同审查</button>
      </nav>
      <div class="topbar-actions"><span class="service-state"><i></i>顾问在线</span><el-button text circle aria-label="消息"><el-icon><Message /></el-icon></el-button><el-avatar :size="32" :icon="UserFilled" /></div>
    </header>

    <transition name="view-fade" mode="out-in">
      <section v-if="activeView === 'finder'" key="finder" class="view-surface finder-view">
        <section class="workspace-header">
          <div><p class="eyebrow">智能租住工作台</p><h1>在真实房源中，快速确定下一处住处</h1><p class="workspace-copy">预算、区域与通勤偏好由租赁顾问连续理解，推荐与预约统一留在同一条业务链路。</p></div>
          <div class="market-status"><span>实时房源目录</span><strong>{{ houses.length }} 套可浏览房源</strong><small>推荐结果会覆盖当前目录</small></div>
        </section>

        <section class="filters" aria-label="房源筛选">
          <div class="filter-field keyword-field"><label>区域或小区</label><el-input v-model="keyword" :prefix-icon="Search" placeholder="例如：安福路、静安寺、陆家嘴" clearable /></div>
          <div class="filter-field"><label>城市</label><el-select v-model="city" placeholder="全部城市"><el-option v-for="item in cityOptions" :key="item" :label="item" :value="item" /></el-select></div>
          <div class="filter-field"><label>意向区域</label><el-select v-model="districts" multiple collapse-tags placeholder="不限"><el-option v-for="item in districtOptions" :key="item" :label="item" :value="item" /></el-select></div>
          <div class="filter-field budget-field"><label>月租预算 <span>{{ budget[0] / 1000 }}k - {{ budget[1] / 1000 }}k</span></label><el-slider v-model="budget" range :min="500" :max="20000" :step="500" :show-tooltip="false" /></div>
          <el-button class="filter-button" type="primary" :icon="Search" :loading="chatLoading" @click="runSearch">获取推荐</el-button>
        </section>

        <div class="content-grid">
          <section class="listing-section"><div class="section-heading"><div><p class="eyebrow">房源结果</p><h2>{{ sortedHouses.length }} 套房源</h2></div><el-segmented v-model="activeSort" :options="[{ label: '智能排序', value: 'recommend' }, { label: '最新发布', value: 'latest' }, { label: '价格优先', value: 'price' }]" /></div>
            <div class="listing-toolbar"><span>{{ activeSort === 'recommend' ? '根据当前需求排序' : activeSort === 'latest' ? '按房源编号倒序' : '按月租从低到高' }}</span><span>房源信息只读</span></div>
            <div class="property-grid"><article v-for="house in sortedHouses" :key="house.id" class="property-card" :class="{ 'is-reserved': reservedHouseIds.includes(String(house.id)) }">
              <div class="property-image"><img v-if="!imageFailures.has(String(house.id))" :src="house.image" :alt="house.title" @error="imageFailed(house)" /><div v-else class="image-fallback"><House /><span>房源图片加载失败</span></div><span v-if="house.preview_image" class="preview-badge">预览图</span><span v-if="reservedHouseIds.includes(String(house.id))" class="reserved-badge">已预约</span><span v-if="house.score" class="match-score"><Star /> {{ house.score }}% 匹配</span><button class="favorite" aria-label="收藏房源"><el-icon><Star /></el-icon></button></div>
              <div class="property-info"><div class="property-title-row"><h3>{{ house.title }}</h3><span class="price">{{ Number(house.price).toLocaleString() }}<small>元/月</small></span></div><p class="location"><el-icon><Location /></el-icon>{{ house.location }} · {{ house.district }}</p><p class="property-spec"><span>{{ roomLabel(house.rooms) }}</span><i></i><span>{{ house.size }}</span><i></i><span>{{ house.metro }}</span></p><div class="tag-row"><el-tag v-for="tag in house.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag></div><div class="property-actions"><el-button text :icon="ArrowRight">查看详情</el-button><el-button type="primary" plain @click="openBooking(house)">预约看房</el-button></div></div>
            </article></div><el-empty v-if="!sortedHouses.length && !chatLoading" description="当前条件下没有返回房源，请调整筛选条件。" />
          </section>

          <aside class="assistant-column"><section class="building-card"><div class="building-copy"><p class="eyebrow">通勤雷达</p><h2>围绕生活半径找房</h2><p>真实房源和预约状态实时联动</p></div><HouseScene /></section>
            <section class="assistant-card"><div class="assistant-header"><div class="assistant-avatar"><el-icon><ChatDotRound /></el-icon></div><div><h2>租赁顾问</h2><p><i></i>当前会话可连续追问</p></div><div class="assistant-actions"><el-button text :icon="Plus" :disabled="chatLoading" @click="startNewConversation">新对话</el-button><el-button text circle aria-label="设置"><el-icon><Setting /></el-icon></el-button></div></div><el-scrollbar ref="chatScroll" class="chat-history"><div v-for="(message, index) in messages" :key="index" class="chat-message" :class="message.role"><p>{{ message.content }}</p></div><div v-if="chatLoading" class="chat-message assistant typing"><span></span><span></span><span></span></div></el-scrollbar><div class="chat-suggestions"><button @click="selectSuggestion('预算 8000，在静安找一居室')">静安一居</button><button @click="selectSuggestion('帮我找距离地铁近的两居室')">地铁两居</button></div><div class="chat-input"><el-input v-model="chatInput" type="textarea" :rows="2" resize="none" placeholder="描述你的租房需求或继续补充条件" @keydown.enter.exact.prevent="sendMessage" /><el-button type="primary" circle :loading="chatLoading" aria-label="发送" @click="sendMessage"><el-icon><ArrowRight /></el-icon></el-button></div></section>
            <section class="service-card"><el-icon><CollectionTag /></el-icon><div><strong>服务保障</strong><p>真实房源核验 · 一对一带看 · 签约支持</p></div><el-icon class="service-arrow"><ArrowRight /></el-icon></section>
          </aside>
        </div>
      </section>

      <section v-else-if="activeView === 'bookings'" key="bookings" class="view-surface record-view"><div class="page-heading"><div><p class="eyebrow">预约中心</p><h1>我的预约</h1><p>查询、确认和取消看房工单。</p></div><el-icon><Tickets /></el-icon></div><div class="appointment-query"><el-input v-model="appointmentPhone" placeholder="预约手机号" clearable @keyup.enter="loadAppointments" /><el-button type="primary" :icon="RefreshRight" :loading="appointmentsLoading" @click="loadAppointments">查询预约</el-button></div><el-alert v-if="appointmentsError" :title="appointmentsError" type="error" :closable="false" show-icon /><div v-if="appointments.length" class="appointment-grid"><article v-for="appointment in appointments" :key="appointment.order_id" class="appointment-card" :class="{ cancelled: appointment.status === 'cancelled' }"><div class="appointment-card-header"><el-icon><Tickets /></el-icon><div><h3>{{ appointment.title }}</h3><p>工单 {{ appointment.order_id }}</p></div><el-tag :type="appointment.status === 'cancelled' ? 'info' : 'success'" effect="light">{{ appointment.status === 'cancelled' ? '已取消' : '预约确认' }}</el-tag></div><dl><div><dt>看房时间</dt><dd>{{ formatAppointmentTime(appointment.viewing_time) }}</dd></div><div><dt>联系电话</dt><dd>{{ appointment.phone_number }}</dd></div></dl><div class="appointment-card-actions"><span>{{ appointment.created_at ? `提交于 ${formatAppointmentTime(appointment.created_at)}` : '预约工单已生成' }}</span><el-button v-if="appointment.status !== 'cancelled'" text type="danger" :icon="CloseBold" @click="cancelAppointment(appointment)">取消预约</el-button></div></article></div><el-empty v-else-if="!appointmentsLoading" description="输入预约手机号后查询工单" /></section>

      <section v-else key="contracts" class="view-surface record-view"><div class="page-heading"><div><p class="eyebrow">RAG 合同审查</p><h1>合同风险分析</h1><p>检索租赁规则依据，再标记合同中需要协商的条款。</p></div><el-icon><Document /></el-icon></div><div class="contract-workspace"><el-input v-model="contractText" type="textarea" :rows="10" resize="vertical" placeholder="粘贴租房合同条款，例如押金、租金、违约责任、维修和房东入户约定" /><el-button type="primary" :loading="contractLoading" @click="analyzeContract">开始分析</el-button></div><el-alert v-if="contractError" :title="contractError" type="error" :closable="false" show-icon /><template v-if="contractAnalysis"><div class="analysis-summary"><strong>{{ contractAnalysis.summary }}</strong><span>{{ contractAnalysis.disclaimer }}</span></div><div v-if="contractAnalysis.risks.length" class="risk-grid"><article v-for="risk in contractAnalysis.risks" :key="`${risk.category}-${risk.clause}`" class="risk-card" :class="risk.level"><div><el-tag :type="risk.level === 'high' ? 'danger' : 'warning'" effect="light">{{ risk.level === 'high' ? '高风险' : '需关注' }}</el-tag><strong>{{ risk.category }}</strong></div><p>{{ risk.clause }}</p><small>{{ risk.suggestion }}</small></article></div><el-empty v-else description="未识别到预设风险关键词，仍建议核对金额、期限和签约主体。" /><section class="knowledge-panel"><div><p class="eyebrow">RAG 检索依据</p><h2>与当前条款相关的审查知识</h2></div><article v-for="item in contractAnalysis.knowledge" :key="item.topic"><strong>{{ item.topic }}</strong><p>{{ item.content }}</p><small>{{ item.source }}</small></article></section></template></section>
    </transition>

    <el-dialog v-model="bookingDialog" width="460" class="booking-dialog" destroy-on-close><template #header><div><p class="eyebrow">预约看房</p><h2>{{ selectedHouse?.title }}</h2></div></template><el-result v-if="bookingConfirmed" icon="success" title="预约工单已生成" sub-title="该房源已在找房页置顶标记，顾问将联系你确认行程。"><template #extra><el-button type="primary" @click="bookingDialog = false">完成</el-button></template></el-result><el-form v-else label-position="top"><el-form-item label="意向看房时间"><el-date-picker v-model="bookingForm.time" type="datetime" placeholder="选择日期和时间" style="width: 100%" /></el-form-item><el-form-item label="联系电话" required><el-input v-model="bookingForm.phone" placeholder="用于顾问确认行程" /></el-form-item><el-form-item label="证件号码" required><el-input v-model="bookingForm.idCard" placeholder="用于生成预约工单" /></el-form-item></el-form><template v-if="!bookingConfirmed" #footer><el-button @click="bookingDialog = false">取消</el-button><el-button type="primary" :loading="bookingSaving" @click="submitBooking">确认预约</el-button></template></el-dialog>
  </main>
</template>

<style scoped>
.rental-workspace { --ink: #18332c; --muted: #73827b; --line: #dce5df; --surface: #fff; --subtle: #f4f7f4; --accent: #23715f; --accent-soft: #e4f1ec; --risk: #b84b3e; --warning: #a97925; }
.main-nav button { position: relative; height: 100%; padding: 0; border: 0; background: transparent; color: #6b7972; cursor: pointer; font: inherit; }.main-nav button.active { color: var(--ink); font-weight: 700; }.main-nav button.active::after { content: ''; position: absolute; right: 0; bottom: -1px; left: 0; height: 2px; background: var(--accent); }
.finder-view, .record-view { min-height: calc(100vh - 73px); }.page-heading { display: flex; align-items: flex-end; justify-content: space-between; padding: 42px 0 24px; }.page-heading h1 { margin: 0; color: var(--ink); font-size: 30px; }.page-heading p:not(.eyebrow) { margin: 9px 0 0; color: var(--muted); font-size: 14px; }.page-heading > .el-icon { display: grid; place-items: center; width: 52px; height: 52px; border: 1px solid #cfe4dc; border-radius: 7px; color: var(--accent); background: var(--accent-soft); font-size: 24px; }
.listing-toolbar { display: flex; justify-content: space-between; margin: 0 0 12px; color: var(--muted); font-size: 12px; }.property-image { background: #e1eae5; }.preview-badge, .reserved-badge { position: absolute; top: 11px; left: 11px; padding: 4px 7px; border-radius: 4px; color: #fff; font-size: 10px; }.preview-badge { background: rgba(16, 45, 38, .78); }.reserved-badge { top: 38px; background: var(--accent); box-shadow: 0 3px 10px rgba(21, 85, 68, .28); }.match-score { left: auto; right: 48px; }.image-fallback { display: grid; height: 100%; place-content: center; gap: 8px; color: #4b7165; font-size: 12px; text-align: center; }.image-fallback svg { width: 32px; height: 32px; margin: auto; }.property-card.is-reserved { border: 2px solid var(--accent); }
.assistant-actions { display: flex; align-items: center; gap: 2px; margin-left: auto; }.assistant-actions .el-button { padding-inline: 5px; }.assistant-header { min-height: 65px; }.assistant-card { height: 514px; }.building-card { min-height: 186px; }.building-copy { max-width: 60%; }.building-copy h2 { font-size: 18px; }.chat-suggestions button { transition: background .18s ease, border-color .18s ease; }.chat-suggestions button:hover { border-color: #8ec3b3; background: #eff8f4; }
.appointment-query { display: flex; gap: 10px; width: min(100%, 440px); margin: 0 0 22px; }.appointment-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }.appointment-card { border-radius: 7px; }.contract-workspace { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: end; }.contract-workspace .el-button { height: 32px; }.analysis-summary { display: grid; gap: 6px; margin: 20px 0 14px; padding: 14px 16px; border-left: 3px solid var(--accent); background: var(--subtle); color: var(--ink); }.analysis-summary span { color: var(--muted); font-size: 12px; }.risk-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }.risk-card { border-radius: 7px; }.knowledge-panel { display: grid; grid-template-columns: minmax(220px, .7fr) repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 22px; padding: 20px; border: 1px solid var(--line); border-radius: 7px; background: var(--surface); }.knowledge-panel h2 { margin: 0; color: var(--ink); font-size: 16px; }.knowledge-panel article { padding-left: 12px; border-left: 2px solid #cce2d9; }.knowledge-panel article strong { color: var(--accent); font-size: 13px; }.knowledge-panel article p { margin: 7px 0; color: #53635c; font-size: 12px; line-height: 1.65; }.knowledge-panel article small { color: var(--muted); font-size: 11px; }
.view-fade-enter-active, .view-fade-leave-active { transition: opacity .16s ease; }.view-fade-enter-from, .view-fade-leave-to { opacity: 0; }
@media (max-width: 840px) { .page-heading { padding-top: 30px; }.appointment-grid, .risk-grid { grid-template-columns: 1fr; }.knowledge-panel { grid-template-columns: 1fr; }.contract-workspace { grid-template-columns: 1fr; }.contract-workspace .el-button { width: 100%; }.main-nav { gap: 20px; }.main-nav button { font-size: 13px; } }
@media (max-width: 590px) { .page-heading h1 { font-size: 24px; }.page-heading > .el-icon { width: 42px; height: 42px; }.appointment-query { width: 100%; }.listing-toolbar { align-items: flex-start; flex-direction: column; gap: 4px; }.main-nav { gap: 15px; }.main-nav button { font-size: 12px; }.assistant-actions .el-button:first-child { font-size: 11px; }.match-score { display: none; } }
</style>

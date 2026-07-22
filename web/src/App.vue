<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import {
  ArrowRight, Calendar, ChatDotRound, Check, CloseBold, CollectionTag, Connection, House, Location, Message, Monitor, RefreshRight, Search, Setting, Star, Tickets, UserFilled,
} from '@element-plus/icons-vue'
import HouseScene from './components/HouseScene.vue'
import { askAgent } from './services/agent'

const city = ref('上海')
const districts = ref([])
const budget = ref([5000, 9500])
const keyword = ref('')
const activeTab = ref('recommend')
const chatInput = ref('')
const chatLoading = ref(false)
const threadId = ref('')
const pendingInterrupt = ref(false)
const chatScroll = ref(null)
const bookingDialog = ref(false)
const selectedHouse = ref(null)
const bookingForm = ref({ time: '', phone: '' })
const booked = ref(false)
const bookingDialogV2 = ref(false)
const bookingSaving = ref(false)
const confirmedBooking = ref(false)
const bookingFormV2 = ref({ time: '', phone: '', idCard: '' })
const reservedHouseIds = ref([])
const appointmentPhone = ref(window.localStorage.getItem('house-agent-phone') || '')
const appointments = ref([])
const appointmentsLoading = ref(false)
const appointmentsError = ref('')

const districtsOptions = ['静安', '徐汇', '长宁', '浦东', '杨浦']
const houses = ref([])
const messages = ref([])
const sortedHouses = computed(() => {
  const sorted = [...houses.value]
  if (activeTab.value === 'latest') sorted.sort((left, right) => Number(right.id) - Number(left.id))
  if (activeTab.value === 'price') sorted.sort((left, right) => Number(left.price) - Number(right.price))
  if (activeTab.value === 'recommend') sorted.sort((left, right) => Number(right.score || 0) - Number(left.score || 0))
  return sorted.sort((left, right) => Number(reservedHouseIds.value.includes(String(right.id))) - Number(reservedHouseIds.value.includes(String(left.id))))
})

function applyAgentResponse(response) {
  threadId.value = response.threadId || threadId.value
  if (Array.isArray(response.state.listings)) houses.value = response.state.listings
  pendingInterrupt.value = response.interrupted
  if (response.content) {
    const content = formatAssistantContent(response.content)
    markReservedListing(content)
    messages.value.push({ role: 'assistant', content })
  }
}

function markReservedListing(content) {
  if (!/(成功预约|预约工单已生成|工单号)/.test(content)) return
  const booked = houses.value.find((house) => content.includes(house.title))
  if (booked) reservedHouseIds.value = [...new Set([...reservedHouseIds.value, String(booked.id)])]
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

async function loadCatalog() {
  try {
    const response = await askAgent('', '', false, 'browse_agent')
    if (Array.isArray(response.state.listings)) houses.value = response.state.listings
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `房源初始化失败：${error.message}`, error: true })
  }
}

async function runSearch() {
  if (chatLoading.value) return
  const districtText = districts.value.length ? `，区域 ${districts.value.join('、')}` : ''
  const keywordText = keyword.value ? `，关键词 ${keyword.value}` : ''
  const content = `找房：${city.value}${districtText}，预算 ${budget.value[0]} 到 ${budget.value[1]} 元/月${keywordText}`
  chatLoading.value = true
  try {
    applyAgentResponse(await askAgent(content, threadId.value, pendingInterrupt.value))
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
    applyAgentResponse(await askAgent(content, threadId.value, pendingInterrupt.value))
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `抱歉，${error.message}。请稍后重试。`, error: true })
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatScroll.value) chatScroll.value.setScrollTop(chatScroll.value.wrapRef.scrollHeight, 300)
}

function openBooking(house) {
  selectedHouse.value = house
  booked.value = false
  bookingForm.value = { time: '', phone: '' }
  bookingFormV2.value = { time: '', phone: '', idCard: '' }
  confirmedBooking.value = false
  bookingDialogV2.value = true
}

async function submitBooking() {
  if (!bookingFormV2.value.phone || !bookingFormV2.value.idCard || bookingSaving.value) return
  bookingSaving.value = true
  try {
    let response = await askAgent('', '', false, 'reserve_agent')
    response = await askAgent(selectedHouse.value.title, response.threadId, true, 'reserve_agent')
    response = await askAgent(bookingFormV2.value.phone, response.threadId, true, 'reserve_agent')
    response = await askAgent(bookingFormV2.value.idCard, response.threadId, true, 'reserve_agent')
    messages.value.push({ role: 'assistant', content: formatAssistantContent(response.content) })
    reservedHouseIds.value = [...new Set([...reservedHouseIds.value, String(selectedHouse.value.id)])]
    appointmentPhone.value = bookingFormV2.value.phone.trim()
    window.localStorage.setItem('house-agent-phone', appointmentPhone.value)
    const orderId = response.content.match(/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}/i)?.[0]
    if (orderId) await syncAppointment(orderId)
    confirmedBooking.value = true
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
    viewing_time: bookingFormV2.value.time ? new Date(bookingFormV2.value.time).toISOString() : '',
  }), '', false, 'appointments_agent')
  appointments.value = response.state.appointments || []
}

async function cancelAppointment(appointment) {
  if (!window.confirm(`确认取消“${appointment.title}”的预约吗？`)) return
  appointmentsLoading.value = true
  try {
    const response = await askAgent(JSON.stringify({ action: 'cancel', order_id: appointment.order_id, phone_number: appointmentPhone.value }), '', false, 'appointments_agent')
    appointments.value = response.state.appointments || []
    reservedHouseIds.value = reservedHouseIds.value.filter((houseId) => !houses.value.find((house) => String(house.id) === houseId && house.title === appointment.title))
  } catch (error) {
    appointmentsError.value = `预约取消失败：${error.message}`
  } finally {
    appointmentsLoading.value = false
  }
}

async function confirmBooking() {
  if (!bookingForm.value.time || !bookingForm.value.phone) return
  chatLoading.value = true
  try {
    const time = new Date(bookingForm.value.time).toISOString().slice(0, 10)
    const content = `预约看房：${selectedHouse.value.title}，时间 ${time}，联系电话 ${bookingForm.value.phone}`
    messages.value.push({ role: 'user', content })
    const response = await askAgent(content, threadId.value)
    applyAgentResponse(response)
    booked.value = response.state.booking?.status === 'submitted'
  } catch (error) {
    messages.value.push({ role: 'assistant', content: `预约提交失败：${error.message}`, error: true })
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

onMounted(() => {
  loadCatalog()
  loadAppointments()
})

</script>

<template>
  <main class="app-shell">
    <header class="topbar">
      <a class="brand" href="#" aria-label="住好家首页"><span class="brand-mark"><House /></span><span>住好家</span></a>
      <nav class="main-nav" aria-label="主导航"><a class="active" href="#match">找房</a><a href="#lease">我的预约</a><a href="#guide">租住指南</a></nav>
      <div class="topbar-actions"><span class="service-state"><i></i>顾问在线</span><el-button text circle aria-label="通知"><el-icon><Message /></el-icon></el-button><el-avatar :size="32" :icon="UserFilled" /></div>
    </header>

    <section id="match" class="workspace-header">
      <div>
        <p class="eyebrow">租赁服务工作台</p>
        <h1>把合适的房子，放在你的生活半径里</h1>
        <p class="workspace-copy">基于预算、通勤与居住偏好，实时筛选可约看房源。</p>
      </div>
      <div class="market-status"><span>上海 · 长租市场</span><strong>本周新增 1,248 套</strong><small>数据更新于今天 09:30</small></div>
    </section>

    <section class="filters" aria-label="房源筛选">
      <div class="filter-field keyword-field"><label>搜索区域或小区</label><el-input v-model="keyword" :prefix-icon="Search" placeholder="例如：安福路、静安寺、陆家嘴" clearable /></div>
      <div class="filter-field"><label>城市</label><el-select v-model="city"><el-option label="上海" value="上海" /></el-select></div>
      <div class="filter-field"><label>意向区域</label><el-select v-model="districts" multiple collapse-tags placeholder="不限"><el-option v-for="item in districtsOptions" :key="item" :label="item" :value="item" /></el-select></div>
      <div class="filter-field budget-field"><label>月租预算 <span>{{ budget[0] / 1000 }}k - {{ budget[1] / 1000 }}k</span></label><el-slider v-model="budget" range :min="3000" :max="12000" :step="500" :show-tooltip="false" /></div>
      <el-button class="filter-button" type="primary" :icon="Search" :loading="chatLoading" @click="runSearch">查看匹配</el-button>
    </section>

    <div class="content-grid">
      <section class="listing-section">
        <div class="section-heading"><div><p class="eyebrow">后端匹配结果</p><h2>{{ houses.length }} 套优先房源</h2></div><el-segmented v-model="activeTab" :options="[{ label: '智能排序', value: 'recommend' }, { label: '最新发布', value: 'latest' }, { label: '价格优先', value: 'price' }]" /></div>
        <div class="listing-toolbar"><span>当前排序：{{ activeTab === 'recommend' ? '智能匹配' : activeTab === 'latest' ? '最新发布' : '价格优先' }}</span></div>
        <div class="property-grid">
          <article v-for="house in sortedHouses" :key="house.id" class="property-card" :class="{ 'is-reserved': reservedHouseIds.includes(String(house.id)) }">
            <div class="property-image"><img :src="house.image" :alt="house.title" /><span class="match-score"><Star /> {{ house.score }}% 匹配</span><button class="favorite" aria-label="收藏房源"><el-icon><Star /></el-icon></button></div>
            <div class="property-info"><div class="property-title-row"><h3>{{ house.title }}</h3><span class="price">{{ house.price.toLocaleString() }}<small>元/月</small></span></div><p class="location"><el-icon><Location /></el-icon>{{ house.location }} · {{ house.district }}</p><p class="property-spec"><span>{{ house.rooms }}</span><i></i><span>{{ house.size }}</span><i></i><span>{{ house.metro }}</span></p><div class="tag-row"><el-tag v-for="tag in house.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag></div><div class="property-actions"><el-button text :icon="ArrowRight">查看详情</el-button><el-button type="primary" plain @click="openBooking(house)">预约看房</el-button></div></div>
          </article>
        </div>
        <el-empty v-if="!houses.length && !chatLoading" description="后端没有返回符合当前条件的房源，请放宽筛选条件。" />
      </section>

      <aside class="assistant-column">
        <section class="building-card"><div class="building-copy"><p class="eyebrow">房源雷达</p><h2>通勤 35 分钟内</h2><p>已覆盖 42 个可约小区</p><button>调整通勤地点 <el-icon><ArrowRight /></el-icon></button></div><HouseScene /></section>
        <section class="assistant-card"><div class="assistant-header"><div class="assistant-avatar"><el-icon><ChatDotRound /></el-icon></div><div><h2>租赁顾问</h2><p><i></i>正在为你服务</p></div><el-button text circle aria-label="设置"><el-icon><Setting /></el-icon></el-button></div><el-scrollbar ref="chatScroll" class="chat-history"><div v-for="(message, index) in messages" :key="index" class="chat-message" :class="message.role"><p>{{ message.content }}</p></div><div v-if="chatLoading" class="chat-message assistant typing"><span></span><span></span><span></span></div></el-scrollbar><div class="chat-suggestions"><button @click="selectSuggestion('预算 8000，在静安找一居室')">静安一居</button><button @click="selectSuggestion('帮我预约安福路公寓')">预约看房</button></div><div class="chat-input"><el-input v-model="chatInput" type="textarea" :rows="2" resize="none" placeholder="描述你的租房需求" @keydown.enter.exact.prevent="sendMessage" /><el-button type="primary" circle :loading="chatLoading" aria-label="发送" @click="sendMessage"><el-icon><ArrowRight /></el-icon></el-button></div></section>
        <section class="service-card"><el-icon><CollectionTag /></el-icon><div><strong>服务保障</strong><p>真实房源核验 · 一对一带看 · 签约支持</p></div><el-icon class="service-arrow"><ArrowRight /></el-icon></section>
      </aside>
    </div>

    <section id="lease" class="appointment-section">
      <div class="appointment-heading"><div><p class="eyebrow">预约中心</p><h2>我的预约</h2></div><div class="appointment-query"><el-input v-model="appointmentPhone" placeholder="预约手机号" clearable @keyup.enter="loadAppointments" /><el-button type="primary" :icon="RefreshRight" :loading="appointmentsLoading" @click="loadAppointments">查询</el-button></div></div>
      <el-alert v-if="appointmentsError" :title="appointmentsError" type="error" :closable="false" show-icon />
      <div v-if="appointments.length" class="appointment-grid">
        <article v-for="appointment in appointments" :key="appointment.order_id" class="appointment-card" :class="{ cancelled: appointment.status === 'cancelled' }">
          <div class="appointment-card-header"><el-icon><Tickets /></el-icon><div><h3>{{ appointment.title }}</h3><p>工单 {{ appointment.order_id }}</p></div><el-tag :type="appointment.status === 'cancelled' ? 'info' : 'success'" effect="light">{{ appointment.status === 'cancelled' ? '已取消' : '预约确认' }}</el-tag></div>
          <dl><div><dt>看房时间</dt><dd>{{ formatAppointmentTime(appointment.viewing_time) }}</dd></div><div><dt>联系电话</dt><dd>{{ appointment.phone_number }}</dd></div></dl>
          <div class="appointment-card-actions"><span>{{ appointment.created_at ? `提交于 ${formatAppointmentTime(appointment.created_at)}` : '预约工单已生成' }}</span><el-button v-if="appointment.status !== 'cancelled'" text type="danger" :icon="CloseBold" @click="cancelAppointment(appointment)">取消预约</el-button></div>
        </article>
      </div>
      <el-empty v-else-if="!appointmentsLoading" description="暂无预约记录" />
    </section>

    <el-dialog v-model="bookingDialog" width="460" class="booking-dialog" destroy-on-close>
      <template #header><div><p class="eyebrow">预约看房</p><h2>{{ selectedHouse?.title }}</h2></div></template>
      <el-result v-if="booked" icon="success" title="预约申请已提交" sub-title="顾问将在 15 分钟内与你确认具体安排。"><template #extra><el-button type="primary" @click="bookingDialog = false">知道了</el-button></template></el-result>
      <el-form v-else label-position="top"><el-form-item label="意向看房时间"><el-date-picker v-model="bookingForm.time" type="datetime" placeholder="选择日期和时间" style="width: 100%" /></el-form-item><el-form-item label="联系电话"><el-input v-model="bookingForm.phone" placeholder="便于顾问确认行程" /></el-form-item><el-alert title="提交后将为你锁定优先带看名额。" type="info" :closable="false" show-icon /></el-form><template v-if="!booked" #footer><el-button @click="bookingDialog = false">取消</el-button><el-button type="primary" :icon="Calendar" @click="confirmBooking">提交申请</el-button></template>
    </el-dialog>

    <el-dialog v-model="bookingDialogV2" width="460" class="booking-dialog" destroy-on-close>
      <template #header><div><p class="eyebrow">预约看房</p><h2>{{ selectedHouse?.title }}</h2></div></template>
      <el-result v-if="confirmedBooking" icon="success" title="预约工单已生成" sub-title="该房源已在列表中置顶标记，顾问将联系您确认行程。"><template #extra><el-button type="primary" @click="bookingDialogV2 = false">完成</el-button></template></el-result>
      <el-form v-else label-position="top">
        <el-form-item label="意向看房时间"><el-date-picker v-model="bookingFormV2.time" type="datetime" placeholder="选择日期和时间" style="width: 100%" /></el-form-item>
        <el-form-item label="联系电话" required><el-input v-model="bookingFormV2.phone" placeholder="用于顾问确认行程" /></el-form-item>
        <el-form-item label="证件号码" required><el-input v-model="bookingFormV2.idCard" placeholder="用于生成预约工单" /></el-form-item>
      </el-form>
      <template v-if="!confirmedBooking" #footer><el-button @click="bookingDialogV2 = false">取消</el-button><el-button type="primary" :loading="bookingSaving" @click="submitBooking">确认预约</el-button></template>
    </el-dialog>

  </main>
</template>

<style scoped>
.property-image:has(img:not([src])), .property-image:has(img[src=""]) {
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #e9f0ea, #d6e2dc);
}

.property-image:has(img:not([src]))::before, .property-image:has(img[src=""])::before {
  content: 'Database record';
  padding: 6px 9px;
  border: 1px solid rgba(42, 122, 105, .24);
  border-radius: 4px;
  color: #37685d;
  font-size: 11px;
  font-weight: 650;
}

.property-image:has(img:not([src])) .match-score, .property-image:has(img[src=""]) .match-score {
  display: none;
}

.listing-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 12px;
  color: #6e7c75;
  font-size: 12px;
}

.property-card {
  position: relative;
}

.property-card.is-reserved {
  border: 2px solid #287464;
  box-shadow: 0 10px 24px rgba(38, 102, 90, .18);
  order: -1;
}

.property-card.is-reserved::after {
  content: '预约已确认';
  position: absolute;
  z-index: 2;
  top: 12px;
  right: 12px;
  padding: 5px 8px;
  border-radius: 4px;
  background: #287464;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}

.property-card.is-reserved .favorite {
  top: 46px;
}

.appointment-section {
  margin-top: 42px;
  padding-top: 26px;
  border-top: 1px solid #dfe7e2;
}

.appointment-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.appointment-heading h2 {
  margin: 0;
  color: #1e2926;
  font-size: 22px;
}

.appointment-query {
  display: flex;
  gap: 8px;
  width: min(100%, 350px);
}

.appointment-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.appointment-card {
  padding: 17px;
  border: 1px solid #dce7e1;
  border-left: 3px solid #287464;
  border-radius: 7px;
  background: #fff;
}

.appointment-card.cancelled {
  border-left-color: #a0aaa5;
  opacity: .7;
}

.appointment-card-header {
  display: flex;
  align-items: flex-start;
  gap: 9px;
}

.appointment-card-header > .el-icon {
  margin-top: 2px;
  color: #287464;
  font-size: 20px;
}

.appointment-card-header h3 {
  margin: 0;
  color: #26372f;
  font-size: 15px;
}

.appointment-card-header p {
  margin: 5px 0 0;
  color: #82908a;
  font-size: 11px;
  word-break: break-all;
}

.appointment-card-header .el-tag {
  margin-left: auto;
  flex: none;
}

.appointment-card dl {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 16px 0 14px;
}

.appointment-card dt {
  margin-bottom: 4px;
  color: #89958f;
  font-size: 11px;
}

.appointment-card dd {
  margin: 0;
  color: #45564e;
  font-size: 13px;
}

.appointment-card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 11px;
  border-top: 1px solid #edf1ee;
  color: #87928d;
  font-size: 11px;
}

@media (max-width: 700px) {
  .appointment-heading { align-items: flex-start; flex-direction: column; }
  .appointment-query { width: 100%; }
  .appointment-grid { grid-template-columns: 1fr; }
}

</style>

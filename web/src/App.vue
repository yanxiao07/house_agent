<script setup>
import { computed, nextTick, ref } from 'vue'
import {
  ArrowRight, Calendar, ChatDotRound, Check, CollectionTag, Connection, House, Location, Message, Monitor, Search, Setting, Star, UserFilled,
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
const chatScroll = ref(null)
const bookingDialog = ref(false)
const selectedHouse = ref(null)
const bookingForm = ref({ time: '', phone: '' })
const booked = ref(false)

const districtsOptions = ['静安', '徐汇', '长宁', '浦东', '杨浦']
const houses = [
  { id: 1, title: '衡复风貌区 · 安福路公寓', district: '徐汇', location: '安福路 218 弄', price: 8200, rooms: '1 室 1 厅', size: '58 m²', metro: '步行 6 分钟', score: 96, image: 'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=920&q=85', tags: ['整租', '近地铁', '朝南'] },
  { id: 2, title: '大宁国际 · 高区两居', district: '静安', location: '广中西路 288 弄', price: 9300, rooms: '2 室 1 厅', size: '73 m²', metro: '步行 8 分钟', score: 92, image: 'https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=920&q=85', tags: ['电梯', '可做饭', '采光好'] },
  { id: 3, title: '古北新城 · 品质一居', district: '长宁', location: '荣华东道 96 弄', price: 7600, rooms: '1 室 1 厅', size: '52 m²', metro: '步行 9 分钟', score: 89, image: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=920&q=85', tags: ['独立阳台', '有车位', '精装'] },
  { id: 4, title: '前滩 · 江景次新房', district: '浦东', location: '东育路 255 弄', price: 9800, rooms: '1 室 1 厅', size: '61 m²', metro: '步行 5 分钟', score: 87, image: 'https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?auto=format&fit=crop&w=920&q=85', tags: ['新房源', '近商圈', '智能门锁'] },
]

const messages = ref([
  { role: 'assistant', content: '你好，我是住好家租赁顾问。告诉我预算、区域或通勤地点，我会为你缩小范围。' },
])

const visibleHouses = computed(() => houses.filter((house) => {
  const keywordMatch = !keyword.value || `${house.title}${house.district}${house.location}`.includes(keyword.value)
  const districtMatch = !districts.value.length || districts.value.includes(house.district)
  return keywordMatch && districtMatch && house.price >= budget.value[0] && house.price <= budget.value[1]
}))

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
    const response = await askAgent(content, threadId.value)
    threadId.value = response.threadId || threadId.value
    messages.value.push({ role: 'assistant', content: response.content })
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
  bookingDialog.value = true
}

function confirmBooking() {
  booked.value = true
  messages.value.push({ role: 'assistant', content: `已收到 ${selectedHouse.value.title} 的看房申请。顾问会通过 ${bookingForm.value.phone || '预留联系方式'} 与你确认。` })
}
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
      <el-button class="filter-button" type="primary" :icon="Search">查看匹配</el-button>
    </section>

    <div class="content-grid">
      <section class="listing-section">
        <div class="section-heading"><div><p class="eyebrow">为你匹配</p><h2>{{ visibleHouses.length }} 套优先房源</h2></div><el-segmented v-model="activeTab" :options="[{ label: '智能排序', value: 'recommend' }, { label: '最新发布', value: 'latest' }, { label: '价格优先', value: 'price' }]" /></div>
        <div class="property-grid">
          <article v-for="house in visibleHouses" :key="house.id" class="property-card">
            <div class="property-image"><img :src="house.image" :alt="house.title" /><span class="match-score"><Star /> {{ house.score }}% 匹配</span><button class="favorite" aria-label="收藏房源"><el-icon><Star /></el-icon></button></div>
            <div class="property-info"><div class="property-title-row"><h3>{{ house.title }}</h3><span class="price">{{ house.price.toLocaleString() }}<small>元/月</small></span></div><p class="location"><el-icon><Location /></el-icon>{{ house.location }} · {{ house.district }}</p><p class="property-spec"><span>{{ house.rooms }}</span><i></i><span>{{ house.size }}</span><i></i><span>{{ house.metro }}</span></p><div class="tag-row"><el-tag v-for="tag in house.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag></div><div class="property-actions"><el-button text :icon="ArrowRight">查看详情</el-button><el-button type="primary" plain @click="openBooking(house)">预约看房</el-button></div></div>
          </article>
        </div>
        <el-empty v-if="!visibleHouses.length" description="没有符合当前条件的房源，请放宽筛选条件。" />
      </section>

      <aside class="assistant-column">
        <section class="building-card"><div class="building-copy"><p class="eyebrow">房源雷达</p><h2>通勤 35 分钟内</h2><p>已覆盖 42 个可约小区</p><button>调整通勤地点 <el-icon><ArrowRight /></el-icon></button></div><HouseScene /></section>
        <section class="assistant-card"><div class="assistant-header"><div class="assistant-avatar"><el-icon><ChatDotRound /></el-icon></div><div><h2>租赁顾问</h2><p><i></i>正在为你服务</p></div><el-button text circle aria-label="设置"><el-icon><Setting /></el-icon></el-button></div><el-scrollbar ref="chatScroll" class="chat-history"><div v-for="(message, index) in messages" :key="index" class="chat-message" :class="message.role"><p>{{ message.content }}</p></div><div v-if="chatLoading" class="chat-message assistant typing"><span></span><span></span><span></span></div></el-scrollbar><div class="chat-suggestions"><button @click="selectSuggestion('预算 8000，在静安找一居室')">静安一居</button><button @click="selectSuggestion('帮我预约安福路公寓')">预约看房</button></div><div class="chat-input"><el-input v-model="chatInput" type="textarea" :rows="2" resize="none" placeholder="描述你的租房需求" @keydown.enter.exact.prevent="sendMessage" /><el-button type="primary" circle :loading="chatLoading" aria-label="发送" @click="sendMessage"><el-icon><ArrowRight /></el-icon></el-button></div></section>
        <section class="service-card"><el-icon><CollectionTag /></el-icon><div><strong>服务保障</strong><p>真实房源核验 · 一对一带看 · 签约支持</p></div><el-icon class="service-arrow"><ArrowRight /></el-icon></section>
      </aside>
    </div>

    <el-dialog v-model="bookingDialog" width="460" class="booking-dialog" destroy-on-close>
      <template #header><div><p class="eyebrow">预约看房</p><h2>{{ selectedHouse?.title }}</h2></div></template>
      <el-result v-if="booked" icon="success" title="预约申请已提交" sub-title="顾问将在 15 分钟内与你确认具体安排。"><template #extra><el-button type="primary" @click="bookingDialog = false">知道了</el-button></template></el-result>
      <el-form v-else label-position="top"><el-form-item label="意向看房时间"><el-date-picker v-model="bookingForm.time" type="datetime" placeholder="选择日期和时间" style="width: 100%" /></el-form-item><el-form-item label="联系电话"><el-input v-model="bookingForm.phone" placeholder="便于顾问确认行程" /></el-form-item><el-alert title="提交后将为你锁定优先带看名额。" type="info" :closable="false" show-icon /></el-form><template v-if="!booked" #footer><el-button @click="bookingDialog = false">取消</el-button><el-button type="primary" :icon="Calendar" @click="confirmBooking">提交申请</el-button></template>
    </el-dialog>
  </main>
</template>

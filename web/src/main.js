import { createApp } from 'vue'
import {
  ElAlert,
  ElAvatar,
  ElButton,
  ElDatePicker,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElOption,
  ElResult,
  ElScrollbar,
  ElSegmented,
  ElSelect,
  ElSlider,
  ElTag,
} from 'element-plus'
import 'element-plus/es/components/alert/style/css'
import 'element-plus/es/components/avatar/style/css'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/date-picker/style/css'
import 'element-plus/es/components/dialog/style/css'
import 'element-plus/es/components/empty/style/css'
import 'element-plus/es/components/form/style/css'
import 'element-plus/es/components/icon/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/option/style/css'
import 'element-plus/es/components/result/style/css'
import 'element-plus/es/components/scrollbar/style/css'
import 'element-plus/es/components/segmented/style/css'
import 'element-plus/es/components/select/style/css'
import 'element-plus/es/components/slider/style/css'
import 'element-plus/es/components/tag/style/css'
import './styles.css'
import App from './App.vue'

const app = createApp(App);

[
  ElAlert,
  ElAvatar,
  ElButton,
  ElDatePicker,
  ElDialog,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElIcon,
  ElInput,
  ElOption,
  ElResult,
  ElScrollbar,
  ElSegmented,
  ElSelect,
  ElSlider,
  ElTag,
].forEach((component) => app.component(component.name, component))

app.mount('#app')

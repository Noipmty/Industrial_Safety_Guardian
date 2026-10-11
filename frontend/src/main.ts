import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { useAuthStore } from '@/stores/auth'

// Vant 按需引入
import {
  Button as VanButton,
  Tabbar as VanTabbar,
  TabbarItem as VanTabbarItem,
  Icon as VanIcon,
  Cell as VanCell,
  CellGroup as VanCellGroup
} from 'vant'
import 'vant/lib/index.css'

// Element Plus 按需引入
import {
  ElButton,
  ElInput,
  ElForm,
  ElFormItem,
  ElTable,
  ElTableColumn,
  ElMenu,
  ElMenuItem,
  ElSubMenu,
  ElIcon,
  ElContainer,
  ElHeader,
  ElMain,
  ElAside,
  ElCard,
  ElDialog,
  ElPagination,
  ElTag,
  ElTabs,
  ElTabPane,
  ElUpload,
  ElProgress,
  ElDescriptions,
  ElDescriptionsItem,
  ElStatistic,
  ElMessage,
  ElMessageBox,
  ElSelect,
  ElOption,
  ElEmpty,
  ElBadge,
} from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)

// Pinia 状态管理
app.use(createPinia())

// 恢复本地持久化的登录态（刷新页面不丢失登录）
useAuthStore().loadFromStorage()

// 路由
app.use(router)

// Vant 组件注册
app.use(VanButton)
app.use(VanTabbar)
app.use(VanTabbarItem)
app.use(VanIcon)
app.use(VanCell)
app.use(VanCellGroup)

// Element Plus 组件注册
app.use(ElButton)
app.use(ElInput)
app.use(ElForm)
app.use(ElFormItem)
app.use(ElTable)
app.use(ElTableColumn)
app.use(ElMenu)
app.use(ElMenuItem)
app.use(ElSubMenu)
app.use(ElIcon)
app.use(ElContainer)
app.use(ElHeader)
app.use(ElMain)
app.use(ElAside)
app.use(ElCard)
app.use(ElDialog)
app.use(ElPagination)
app.use(ElTag)
app.use(ElTabs)
app.use(ElTabPane)
app.use(ElUpload)
app.use(ElProgress)
app.use(ElDescriptions)
app.use(ElDescriptionsItem)
app.use(ElStatistic)
app.use(ElSelect)
app.use(ElOption)
app.use(ElEmpty)
app.use(ElBadge)

// 全局方法
app.config.globalProperties.$message = ElMessage
app.config.globalProperties.$confirm = ElMessageBox.confirm

app.mount('#app')

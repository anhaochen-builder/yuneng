import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '总览看板' } },
  { path: '/diagnostic', name: 'DiagnosticCenter', component: () => import('@/views/DiagnosticCenter.vue'), meta: { title: '智能诊断中心' } },
  { path: '/scada', name: 'SCADADashboard', component: () => import('@/views/SCADADashboard.vue'), meta: { title: 'SCADA 数据看板' } },
  { path: '/alarms', name: 'AlarmManagement', component: () => import('@/views/AlarmManagement.vue'), meta: { title: '告警管理' } },
  { path: '/trace/:taskId', name: 'DiagnosticTrace', component: () => import('@/views/DiagnosticTrace.vue'), meta: { title: '诊断过程透视' } },
  { path: '/knowledge', name: 'KnowledgeBase', component: () => import('@/views/KnowledgeBase.vue'), meta: { title: '知识库管理' } },
  { path: '/devices', name: 'DeviceStatus', component: () => import('@/views/DeviceStatus.vue'), meta: { title: '设备状态查询' } },
  { path: '/feedback', name: 'FeedbackCenter', component: () => import('@/views/FeedbackCenter.vue'), meta: { title: '反馈与学习' } },
  { path: '/skills', name: 'SkillManagement', component: () => import('@/views/SkillManagement.vue'), meta: { title: '技能管理' } },
  { path: '/settings', name: 'SystemSettings', component: () => import('@/views/SystemSettings.vue'), meta: { title: '系统设置' } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title} - 驭能智能诊断平台`
  next()
})

export default router

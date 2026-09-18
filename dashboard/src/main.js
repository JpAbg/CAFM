import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'

import { registerSW } from 'virtual:pwa-register'

const updateSW = registerSW({
  onNeedRefresh() {
    updateSW(true)
  },
  onOfflineReady() {
    console.log('CAFM is ready to work offline')
  }
})

createApp(App).use(router).mount('#app')
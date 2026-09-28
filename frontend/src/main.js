import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registrarServiceWorker } from './pwa'
import './assets/main.css'

const app = createApp(App)
// O Pinia vem antes do router: os guardas de rota leem o campus lembrado.
app.use(createPinia())
app.use(router)
app.mount('#app')

registrarServiceWorker()

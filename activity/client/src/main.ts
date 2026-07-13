import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { initializeLocale, t } from "./i18n";
import { router } from "./router";
import "./style.css";

initializeLocale();

const app = createApp(App);
app.config.globalProperties.$t = t;
app.use(createPinia()).use(router).mount("#app");

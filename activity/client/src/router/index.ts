import { createRouter, createWebHashHistory } from "vue-router";
import WeAreOmni from "../views/WeAreOmni.vue";
import GetToKnowUs from "../views/GetToKnowUs.vue";
import PanelEntry from "../views/PanelEntry.vue";
import NoAccess from "../views/NoAccess.vue";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "we-are-omni", component: WeAreOmni },
    { path: "/about", name: "get-to-know-us", component: GetToKnowUs },
    { path: "/panel/:module?", name: "panel", component: PanelEntry },
    { path: "/no-access", name: "no-access", component: NoAccess },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

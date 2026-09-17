import { createApp } from 'vue';
import PrimeVue from 'primevue/config';
import Aura from '@primeuix/themes/aura';
import 'primeicons/primeicons.css';

// Empty root component: Vue compiles the in-DOM template of <div id="app">,
// so feature code adds its component tags to resources/views/app.blade.php and
// registers those components on `app` (app.component(...)) before the mount
// call below. Nothing is registered globally here on purpose.
const app = createApp({});

app.use(PrimeVue, { theme: { preset: Aura } });

app.mount('#app');

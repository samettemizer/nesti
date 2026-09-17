# Sidebar

Sidebar is a compound navigation panel with collapsible icon mode, offcanvas mode, variants and optional overlay.

## Variants

Interactive playground for every sidebar variant , collapsible mode, side , overlay , open-on-hover and backdrop.

```vue
<template>
    <div>
        <div class="flex flex-wrap items-start gap-4 mb-4">
            <div class="flex flex-col gap-1.5">
                <Label>Variant</Label>
                <Select v-model="variant" :options="variantOptions" optionLabel="label" optionValue="value" placeholder="Variant" class="w-40" />
            </div>
            <div class="flex flex-col gap-1.5">
                <Label>Collapsible</Label>
                <Select v-model="collapsible" :options="collapsibleOptions" optionLabel="label" optionValue="value" placeholder="Collapsible" class="w-40" />
            </div>
            <div class="flex flex-col gap-1.5">
                <Label>Side</Label>
                <SelectButton v-model="side" :options="sideOptions" optionLabel="label" optionValue="value" :allowEmpty="false" />
            </div>
            <div class="flex flex-col gap-1.5">
                <Label for="overlay-sw">Overlay</Label>
                <ToggleSwitch v-model="overlay" inputId="overlay-sw" />
            </div>
            <div class="flex flex-col gap-1.5">
                <Label for="hover-sw">Open on Hover</Label>
                <ToggleSwitch v-model="openOnHover" inputId="hover-sw" />
            </div>
            <div class="flex flex-col gap-1.5">
                <Label for="backdrop-sw">Backdrop</Label>
                <ToggleSwitch v-model="backdrop" inputId="backdrop-sw" />
            </div>
        </div>
        <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
            <SidebarLayout class="min-h-192! relative!">
                <SidebarBackdrop v-if="(backdrop || isMobile) && open" class="absolute!" />
                <SidebarMain v-if="side === 'right'">
                    <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                        <SidebarTrigger severity="secondary" target="variants-demo" :text="true" size="small">
                            <SidebarIcon />
                        </SidebarTrigger>
                    </header>
                    <div class="flex-1 p-4 flex flex-col gap-4">
                        <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                        <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                    </div>
                </SidebarMain>
                <Sidebar id="variants-demo" :variant="variant" :collapsible="isMobile ? 'offcanvas' : collapsible" :side="side" :overlay="isMobile || overlay" :openOnHover="openOnHover" v-model:open="open">
                    <SidebarSpacer />
                    <SidebarAside>
                        <SidebarPanel>
                            <SidebarHeader>
                                <SidebarMenu>
                                    <SidebarMenuItem>
                                        <SidebarMenuButton class="px-1!">
                                            <div class="flex size-6 shrink-0 items-center justify-center rounded-md bg-linear-to-br from-violet-500 to-indigo-600 text-white text-xs font-bold leading-none">A</div>
                                            <span class="font-semibold text-sm">Acme Inc</span>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                </SidebarMenu>
                            </SidebarHeader>
                            <SidebarContent>
                                <SidebarGroup v-for="group in navGroups" :key="group.label">
                                    <SidebarGroupLabel>{{ group.label }}</SidebarGroupLabel>
                                    <SidebarGroupContent>
                                        <SidebarMenu>
                                            <SidebarMenuItem v-for="item in group.items" :key="item.label" :collapsible="!!item.subItems" :defaultOpen="item.subItems ? item.subItems.some((s) => s.isActive) : undefined">
                                                <SidebarMenuButton :isActive="item.isActive">
                                                    <component :is="item.icon" />
                                                    <span>{{ item.label }}</span>
                                                    <ChevronDown v-if="item.subItems" class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                                </SidebarMenuButton>
                                                <SidebarMenuBadge v-if="item.badge">{{ item.badge }}</SidebarMenuBadge>
                                                <SidebarMenuSub v-if="item.subItems">
                                                    <SidebarMenuSubItem v-for="sub in item.subItems" :key="sub.label">
                                                        <SidebarMenuSubButton :isActive="sub.isActive">
                                                            <span>{{ sub.label }}</span>
                                                        </SidebarMenuSubButton>
                                                    </SidebarMenuSubItem>
                                                </SidebarMenuSub>
                                                <SidebarMenuAction v-else-if="!item.badge" :showOnHover="true">
                                                    <EllipsisV />
                                                </SidebarMenuAction>
                                            </SidebarMenuItem>
                                        </SidebarMenu>
                                    </SidebarGroupContent>
                                </SidebarGroup>
                            </SidebarContent>
                            <SidebarFooter>
                                <SidebarMenu>
                                    <SidebarMenuItem>
                                        <SidebarMenuButton class="p-1!">
                                            <Avatar label="JD" shape="circle" class="size-6 shrink-0 text-xs" />
                                            <span>John Doe</span>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                </SidebarMenu>
                            </SidebarFooter>
                            <SidebarRail />
                        </SidebarPanel>
                    </SidebarAside>
                </Sidebar>
                <SidebarMain v-if="side === 'left'">
                    <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                        <SidebarTrigger severity="secondary" target="variants-demo" :text="true" size="small">
                            <SidebarIcon />
                        </SidebarTrigger>
                    </header>
                    <div class="flex-1 p-4 flex flex-col gap-4">
                        <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                        <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                    </div>
                </SidebarMain>
            </SidebarLayout>
        </div>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import Bell from '@primeicons/vue/bell';
import CalendarIcon from '@primeicons/vue/calendar';
import ChartBar from '@primeicons/vue/chart-bar';
import ChevronDown from '@primeicons/vue/chevron-down';
import CreditCard from '@primeicons/vue/credit-card';
import EllipsisV from '@primeicons/vue/ellipsis-v';
import Folder from '@primeicons/vue/folder';
import Home from '@primeicons/vue/home';
import Inbox from '@primeicons/vue/inbox';
import Search from '@primeicons/vue/search';
import ShoppingCart from '@primeicons/vue/shopping-cart';
import SidebarIcon from '@primeicons/vue/sidebar';
import Star from '@primeicons/vue/star';
import Users from '@primeicons/vue/users';

const isMobile = ref(false);
const open = ref(true);
const variant = ref('sidebar');
const collapsible = ref('icon');
const side = ref('left');
const overlay = ref(false);
const openOnHover = ref(false);
const backdrop = ref(false);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    open.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        open.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});

const variantOptions = [
    { label: 'Sidebar', value: 'sidebar' },
    { label: 'Floating', value: 'floating' },
    { label: 'Inset', value: 'inset' }
];
const collapsibleOptions = [
    { label: 'Icon', value: 'icon' },
    { label: 'Offcanvas', value: 'offcanvas' },
    { label: 'None', value: 'none' }
];
const sideOptions = [
    { label: 'Left', value: 'left' },
    { label: 'Right', value: 'right' }
];
const navGroups = [
    {
        label: 'Navigation',
        items: [
            { icon: Home, label: 'Home', isActive: true },
            { icon: Inbox, label: 'Inbox', badge: '12' },
            { icon: Search, label: 'Search' },
            { icon: Bell, label: 'Notifications', badge: '3' }
        ]
    },
    {
        label: 'Projects',
        items: [
            { icon: ChartBar, label: 'Analytics', subItems: [{ label: 'Overview', isActive: true }, { label: 'Reports' }, { label: 'Real-time' }] },
            { icon: Users, label: 'Team' },
            { icon: CalendarIcon, label: 'Calendar' },
            { icon: Folder, label: 'Documents', subItems: [{ label: 'Shared' }, { label: 'Private' }, { label: 'Archived' }] }
        ]
    },
    {
        label: 'Billing',
        items: [
            { icon: CreditCard, label: 'Payments' },
            { icon: ShoppingCart, label: 'Orders' },
            { icon: Star, label: 'Subscriptions' }
        ]
    }
];
<\/script>
```

## With Menu

Full application chrome with a workspace switcher in the header, grouped navigation and a user menu in the footer using the Menu component. Collapses to icon mode.

```vue
<template>
    <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
        <SidebarLayout class="min-h-192! relative!">
            <SidebarBackdrop v-if="isMobile && open" class="absolute!" />
            <Sidebar id="menu-demo" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="isMobile" v-model:open="open">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!" @click="(e) => $refs.companyMenu.toggle(e)" aria-haspopup="true" aria-controls="company_menu">
                                        <div :class="\`flex size-6 shrink-0 items-center justify-center rounded-md bg-linear-to-br \${activeCompany.color} text-white text-xs font-bold leading-none\`">
                                            {{ activeCompany.logo }}
                                        </div>
                                        <span class="font-semibold text-sm">{{ activeCompany.name }}</span>
                                        <ChevronDown class="ml-auto" />
                                    </SidebarMenuButton>
                                    <Menu ref="companyMenu" id="company_menu" :model="companyMenuItems" :popup="true">
                                        <template #start>
                                            <div class="px-3 py-1 text-sm font-medium text-muted-color">Companies</div>
                                        </template>
                                        <template #item="{ item }">
                                            <div class="flex items-center gap-2 p-2">
                                                <div v-if="item.logo" :class="\`flex size-5 shrink-0 items-center justify-center rounded-sm bg-linear-to-br \${item.color} text-white text-[0.625rem] font-bold leading-none\`">
                                                    {{ item.logo }}
                                                </div>
                                                <span class="text-sm">{{ item.label }}</span>
                                                <Check v-if="item.active" class="ml-auto" />
                                            </div>
                                        </template>
                                        <template #end>
                                            <div class="flex items-center gap-2 p-2 px-3">
                                                <Plus />
                                                <div class="text-sm font-medium text-muted-color">Add company</div>
                                            </div>
                                        </template>
                                    </Menu>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup>
                                <SidebarGroupLabel>Navigation</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton :isActive="true">
                                                <Home />
                                                <span>Home</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Inbox />
                                                <span>Inbox</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Search />
                                                <span>Search</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Users />
                                                <span>Team</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Bell />
                                                <span>Notifications</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>

                        <SidebarFooter>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!" @click="(e) => $refs.userMenu.toggle(e)" aria-haspopup="true" aria-controls="user_menu">
                                        <Avatar label="JD" shape="circle" class="size-6 shrink-0 text-xs" />
                                        <span>John Doe</span>
                                        <ChevronDown class="ml-auto" />
                                    </SidebarMenuButton>
                                    <Menu ref="userMenu" id="user_menu" :model="userMenuItems" :popup="true">
                                        <template #start>
                                            <div class="px-3 py-1 text-xs font-medium text-muted-color">john@acme.com</div>
                                        </template>
                                    </Menu>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarFooter>
                        <SidebarRail />
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <SidebarMain>
                <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                    <SidebarTrigger severity="secondary" target="menu-demo" :text="true" size="small">
                        <SidebarIcon />
                    </SidebarTrigger>
                </header>
                <div class="flex-1 p-4 flex flex-col gap-4">
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                </div>
            </SidebarMain>
        </SidebarLayout>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import Bell from '@primeicons/vue/bell';
import Check from '@primeicons/vue/check';
import ChevronDown from '@primeicons/vue/chevron-down';
import Cog from '@primeicons/vue/cog';
import Home from '@primeicons/vue/home';
import Inbox from '@primeicons/vue/inbox';
import Plus from '@primeicons/vue/plus';
import Search from '@primeicons/vue/search';
import SidebarIcon from '@primeicons/vue/sidebar';
import SignOut from '@primeicons/vue/sign-out';
import Users from '@primeicons/vue/users';

const isMobile = ref(false);
const open = ref(true);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    open.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        open.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});

const companies = [
    { name: 'Acme Inc', logo: 'A', color: 'from-violet-500 to-indigo-600' },
    { name: 'Globex Corp', logo: 'G', color: 'from-emerald-500 to-teal-600' },
    { name: 'Initech', logo: 'I', color: 'from-orange-500 to-red-600' }
];
const activeCompany = ref({ name: 'Acme Inc', logo: 'A', color: 'from-violet-500 to-indigo-600' });
const userMenuItems = [{ label: 'Settings', icon: Cog }, { label: 'Notifications', icon: Bell }, { separator: true }, { label: 'Sign out', icon: SignOut }];
const companyMenuItems = computed(() => [
    ...companies.map((c) => ({
        label: c.name,
        logo: c.logo,
        color: c.color,
        active: activeCompany.value.name === c.name,
        command: () => {
            activeCompany.value = c;
        }
    })),
    { separator: true }
]);
<\/script>
```

## Responsive

Below 1024px the sidebar turns into an offcanvas overlay with a backdrop. Above that it stays in icon mode pushing the inset. Use a matchMedia reactive flag to switch between the two layouts.

```vue
<template>
    <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
        <SidebarLayout class="min-h-192! relative!">
            <SidebarBackdrop v-if="isMobile && open" class="absolute!" />
            <Sidebar id="mobile-nav" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="isMobile" v-model:open="open" width="14rem">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <div class="flex size-6 shrink-0 items-center justify-center rounded-md bg-linear-to-br from-violet-500 to-indigo-600 text-white text-xs font-bold leading-none">A</div>
                                        <span class="font-semibold text-sm">Acme Inc</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup>
                                <SidebarGroupLabel>Menu</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton :isActive="true">
                                                <Home />
                                                <span>Home</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Inbox />
                                                <span>Inbox</span>
                                            </SidebarMenuButton>
                                            <SidebarMenuBadge>3</SidebarMenuBadge>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Search />
                                                <span>Search</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Users />
                                                <span>Team</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Bell />
                                                <span>Notifications</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Cog />
                                                <span>Settings</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>

                        <SidebarFooter>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <Avatar label="JD" shape="circle" class="size-6 shrink-0 text-xs" />
                                        <span>John Doe</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarFooter>
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <SidebarMain>
                <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                    <SidebarTrigger severity="secondary" target="mobile-nav" :text="true" size="small">
                        <SidebarIcon />
                    </SidebarTrigger>
                    <span class="text-sm font-medium">Dashboard</span>
                    <span class="ml-auto text-xs text-muted-color rounded-md bg-surface-100 dark:bg-surface-800 px-2 py-1">{{ isMobile ? 'Mobile' : 'Desktop' }}</span>
                </header>
                <div class="flex-1 p-4 flex flex-col gap-4">
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                </div>
            </SidebarMain>
        </SidebarLayout>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import Bell from '@primeicons/vue/bell';
import Cog from '@primeicons/vue/cog';
import Home from '@primeicons/vue/home';
import Inbox from '@primeicons/vue/inbox';
import Search from '@primeicons/vue/search';
import SidebarIcon from '@primeicons/vue/sidebar';
import Users from '@primeicons/vue/users';

const isMobile = ref(false);
const open = ref(true);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    open.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        open.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});
<\/script>
```

## Dual Sidebar

Two sidebars on opposite sides of the layout: a primary navigation on the left (icon-collapsible) and a secondary AI chat panel on the right (offcanvas). Each SidebarTrigger targets its sidebar by id.

```vue
<template>
    <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
        <SidebarLayout class="min-h-192! relative!">
            <SidebarBackdrop v-if="isMobile && (navOpen || open)" class="absolute!" />
            <!-- Left sidebar - icon collapsible -->
            <Sidebar id="nav" side="left" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="isMobile" v-model:open="navOpen" width="14rem">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <div class="flex size-6 shrink-0 items-center justify-center rounded-md bg-linear-to-br from-violet-500 to-indigo-600 text-white text-xs font-bold leading-none">A</div>
                                        <span class="font-semibold text-sm">Acme Inc</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup>
                                <SidebarGroupLabel>Navigation</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton :isActive="true">
                                                <Home />
                                                <span>Home</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Inbox />
                                                <span>Inbox</span>
                                            </SidebarMenuButton>
                                            <SidebarMenuBadge>5</SidebarMenuBadge>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Search />
                                                <span>Search</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Bell />
                                                <span>Notifications</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>

                            <SidebarGroup>
                                <SidebarGroupLabel>Projects</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem :collapsible="true" :defaultOpen="true">
                                            <SidebarMenuButton>
                                                <ChartBar />
                                                <span>Analytics</span>
                                                <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                            </SidebarMenuButton>
                                            <SidebarMenuSub>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton :isActive="true">Overview</SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>Reports</SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                            </SidebarMenuSub>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Users />
                                                <span>Team</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <CalendarIcon />
                                                <span>Calendar</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>

                        <SidebarFooter>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton>
                                        <Cog />
                                        <span>Settings</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarFooter>
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <!-- Main content -->
            <SidebarMain>
                <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                    <SidebarTrigger target="nav" severity="secondary" :text="true" size="small">
                        <SidebarIcon />
                    </SidebarTrigger>
                    <span class="text-sm font-medium flex-1">Dashboard</span>
                    <SidebarTrigger target="ai" severity="secondary" :text="true" size="small">
                        <Comment />
                    </SidebarTrigger>
                </header>
                <div class="flex-1 p-4 flex flex-col gap-4">
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                </div>
            </SidebarMain>

            <!-- Right sidebar - Claude-style chat, offcanvas -->
            <Sidebar id="ai" side="right" collapsible="offcanvas" overlay v-model:open="open" width="18rem">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <div class="flex items-center gap-2 px-1">
                                <span class="font-semibold text-sm text-surface-500">Weekly metrics overview</span>
                            </div>
                        </SidebarHeader>

                        <SidebarContent>
                            <div class="flex flex-col gap-4 px-3 py-2">
                                <div class="rounded-xl bg-surface-100 dark:bg-surface-800 px-3 py-2.5 text-sm">Show me this week&apos;s metrics</div>

                                <div class="text-sm leading-relaxed">
                                    <p>Here are your key metrics for this week:</p>
                                    <ul class="mt-2 space-y-1.5 text-muted-color">
                                        <li class="flex justify-between">
                                            <span>Page views</span>
                                            <span class="font-medium text-color">12,482</span>
                                        </li>
                                        <li class="flex justify-between">
                                            <span>New users</span>
                                            <span class="font-medium text-color">342</span>
                                        </li>
                                        <li class="flex justify-between">
                                            <span>Bounce rate</span>
                                            <span class="font-medium text-color">34%</span>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </SidebarContent>

                        <SidebarFooter>
                            <div class="mx-1 rounded-xl border border-surface-200 dark:border-surface-700 px-3 py-2.5">
                                <input type="text" placeholder="Reply to Claude..." class="w-full bg-transparent border-none outline-none text-sm" />
                            </div>
                        </SidebarFooter>
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>
        </SidebarLayout>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import Bell from '@primeicons/vue/bell';
import CalendarIcon from '@primeicons/vue/calendar';
import ChartBar from '@primeicons/vue/chart-bar';
import ChevronDown from '@primeicons/vue/chevron-down';
import Cog from '@primeicons/vue/cog';
import Comment from '@primeicons/vue/comment';
import Home from '@primeicons/vue/home';
import Inbox from '@primeicons/vue/inbox';
import Search from '@primeicons/vue/search';
import SidebarIcon from '@primeicons/vue/sidebar';
import Users from '@primeicons/vue/users';

const isMobile = ref(false);
const navOpen = ref(true);
const open = ref(false);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    navOpen.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        navOpen.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});
<\/script>
```

## Multi Sidebar

Two stacked sidebars within a single SidebarLayout : a hover-to-open icon bar (icon mode + overlay) and a secondary panel that stays open on desktop and collapses to an offcanvas overlay on smaller screens. IDE-like layout.

```vue
<template>
    <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
        <SidebarLayout class="min-h-192! relative!">
            <SidebarBackdrop v-if="isMobile && (open || secondaryOpen)" class="absolute!" />
            <!-- Icon bar - always collapsed, opens on hover as overlay -->
            <Sidebar id="iconbar" side="left" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="true" :openOnHover="!isMobile" width="12rem" v-model:open="open">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <div class="flex size-6 shrink-0 items-center justify-center rounded-md bg-emerald-600 text-white text-xs font-bold leading-none">A</div>
                                        <span class="font-semibold text-sm">Acme Inc</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton :isActive="true">
                                                <Home />
                                                <span>Home</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Database />
                                                <span>Database</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Key />
                                                <span>Authentication</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Server />
                                                <span>Edge Functions</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Globe />
                                                <span>Storage</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <Code />
                                                <span>SQL Editor</span>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>

                        <SidebarFooter>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton>
                                        <Cog />
                                        <span>Settings</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarFooter>
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <!-- Secondary sidebar - always open on desktop, offcanvas on mobile -->
            <Sidebar id="secondary" side="left" width="14rem" :collapsible="isMobile ? 'offcanvas' : 'none'" :overlay="isMobile" v-model:open="secondaryOpen">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <div class="px-1">
                                <span class="font-semibold text-sm">Settings</span>
                            </div>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup>
                                <SidebarGroupLabel>Configuration</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton :isActive="true"><span>General</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>Compute and Disk</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>Infrastructure</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>Integrations</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>API Keys</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>JWT Keys</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>Log Drains</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton><span>Add-ons</span></SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>

                            <SidebarGroup>
                                <SidebarGroupLabel>Integrations</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <span>Data API</span>
                                                <ExternalLink class="ml-auto" />
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <span>Vault</span>
                                                <SidebarMenuBadge>BETA</SidebarMenuBadge>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>

                            <SidebarGroup>
                                <SidebarGroupLabel>Billing</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <span>Subscription</span>
                                                <ExternalLink class="ml-auto" />
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton>
                                                <span>Usage</span>
                                                <ExternalLink class="ml-auto" />
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <!-- Main content -->
            <SidebarMain>
                <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                    <SidebarTrigger v-if="isMobile" target="iconbar" severity="secondary" :text="true" size="small">
                        <SidebarIcon />
                    </SidebarTrigger>
                    <SidebarTrigger v-if="isMobile" target="secondary" severity="secondary" :text="true" size="small">
                        <Cog />
                    </SidebarTrigger>
                    <span class="text-sm font-medium">Table Editor</span>
                    <span class="text-xs text-muted-color">/ users</span>
                </header>
                <div class="flex-1 p-4 flex flex-col gap-4">
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                </div>
            </SidebarMain>
        </SidebarLayout>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import Code from '@primeicons/vue/code';
import Cog from '@primeicons/vue/cog';
import Database from '@primeicons/vue/database';
import ExternalLink from '@primeicons/vue/external-link';
import Globe from '@primeicons/vue/globe';
import Home from '@primeicons/vue/home';
import Key from '@primeicons/vue/key';
import Server from '@primeicons/vue/server';
import SidebarIcon from '@primeicons/vue/sidebar';

const isMobile = ref(false);
const open = ref(false);
const secondaryOpen = ref(true);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    secondaryOpen.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        secondaryOpen.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});
<\/script>
```

## Nested Menu

Menu items become collapsible to reveal a nested SidebarMenuSub with deep trees and active-state tracking.

```vue
<template>
    <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
        <SidebarLayout class="min-h-192! relative!">
            <SidebarBackdrop v-if="isMobile && open" class="absolute!" />
            <Sidebar id="nested" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="isMobile" v-model:open="open">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <div class="flex size-6 shrink-0 items-center justify-center rounded-md bg-linear-to-br from-emerald-500 to-teal-600 text-white text-xs font-bold leading-none">F</div>
                                        <span class="font-semibold text-sm">File Manager</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup>
                                <SidebarGroupLabel>Files</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem :collapsible="true" :defaultOpen="true">
                                            <SidebarMenuButton>
                                                <Folder />
                                                <span>Documents</span>
                                                <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                            </SidebarMenuButton>
                                            <SidebarMenuSub>
                                                <SidebarMenuItem :collapsible="true" :defaultOpen="true">
                                                    <SidebarMenuButton>
                                                        <span>Work</span>
                                                        <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                                    </SidebarMenuButton>
                                                    <SidebarMenuSub>
                                                        <SidebarMenuItem :collapsible="true" :defaultOpen="true">
                                                            <SidebarMenuButton>
                                                                <span>Projects</span>
                                                                <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                                            </SidebarMenuButton>
                                                            <SidebarMenuSub>
                                                                <SidebarMenuSubItem>
                                                                    <SidebarMenuSubButton :isActive="true">
                                                                        <span>Q1 Report</span>
                                                                    </SidebarMenuSubButton>
                                                                </SidebarMenuSubItem>
                                                                <SidebarMenuSubItem>
                                                                    <SidebarMenuSubButton>
                                                                        <span>Q2 Report</span>
                                                                    </SidebarMenuSubButton>
                                                                </SidebarMenuSubItem>
                                                                <SidebarMenuSubItem>
                                                                    <SidebarMenuSubButton>
                                                                        <span>Roadmap</span>
                                                                    </SidebarMenuSubButton>
                                                                </SidebarMenuSubItem>
                                                            </SidebarMenuSub>
                                                        </SidebarMenuItem>
                                                        <SidebarMenuSubItem>
                                                            <SidebarMenuSubButton>
                                                                <span>Invoices</span>
                                                            </SidebarMenuSubButton>
                                                        </SidebarMenuSubItem>
                                                        <SidebarMenuSubItem>
                                                            <SidebarMenuSubButton>
                                                                <span>Contracts</span>
                                                            </SidebarMenuSubButton>
                                                        </SidebarMenuSubItem>
                                                    </SidebarMenuSub>
                                                </SidebarMenuItem>
                                                <SidebarMenuItem :collapsible="true">
                                                    <SidebarMenuButton>
                                                        <span>Personal</span>
                                                        <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                                    </SidebarMenuButton>
                                                    <SidebarMenuSub>
                                                        <SidebarMenuSubItem>
                                                            <SidebarMenuSubButton>
                                                                <span>Recipes</span>
                                                            </SidebarMenuSubButton>
                                                        </SidebarMenuSubItem>
                                                        <SidebarMenuSubItem>
                                                            <SidebarMenuSubButton>
                                                                <span>Travel</span>
                                                            </SidebarMenuSubButton>
                                                        </SidebarMenuSubItem>
                                                    </SidebarMenuSub>
                                                </SidebarMenuItem>
                                            </SidebarMenuSub>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>

                            <SidebarGroup>
                                <SidebarGroupLabel>Media</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem :collapsible="true">
                                            <SidebarMenuButton>
                                                <ImageIcon />
                                                <span>Photos</span>
                                                <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                            </SidebarMenuButton>
                                            <SidebarMenuSub>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>2024</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>2025</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                            </SidebarMenuSub>
                                        </SidebarMenuItem>
                                        <SidebarMenuItem :collapsible="true">
                                            <SidebarMenuButton>
                                                <Video />
                                                <span>Videos</span>
                                                <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                            </SidebarMenuButton>
                                            <SidebarMenuSub>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>Tutorials</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>Recordings</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                            </SidebarMenuSub>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>

                            <SidebarGroup>
                                <SidebarGroupLabel>Bookmarks</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem :collapsible="true">
                                            <SidebarMenuButton>
                                                <Globe />
                                                <span>Websites</span>
                                                <ChevronDown class="ml-auto transition-transform duration-200 [[data-open]>&]:rotate-180" />
                                            </SidebarMenuButton>
                                            <SidebarMenuSub>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>Blog</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>Portfolio</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                                <SidebarMenuSubItem>
                                                    <SidebarMenuSubButton>
                                                        <span>Documentation</span>
                                                    </SidebarMenuSubButton>
                                                </SidebarMenuSubItem>
                                            </SidebarMenuSub>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>

                        <SidebarFooter>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <Avatar label="JD" shape="circle" class="size-6 shrink-0 text-xs" />
                                        <span>John Doe</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarFooter>
                        <SidebarRail />
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <SidebarMain>
                <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                    <SidebarTrigger severity="secondary" target="nested" :text="true" size="small">
                        <SidebarIcon />
                    </SidebarTrigger>
                    <span class="text-sm font-medium">File Manager</span>
                </header>
                <div class="flex-1 p-6">
                    <h1 class="text-2xl font-bold mb-4">Q1 Report</h1>
                    <p class="text-muted-color">Documents &gt; Work &gt; Projects &gt; Q1 Report</p>
                </div>
            </SidebarMain>
        </SidebarLayout>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import ChevronDown from '@primeicons/vue/chevron-down';
import Folder from '@primeicons/vue/folder';
import Globe from '@primeicons/vue/globe';
import ImageIcon from '@primeicons/vue/image';
import SidebarIcon from '@primeicons/vue/sidebar';
import Video from '@primeicons/vue/video';

const isMobile = ref(false);
const open = ref(true);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    open.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        open.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});
<\/script>
```

## Chat Application

Chat history sidebar with grouped conversations (Today, Yesterday, Previous 7 days, Previous 30 days). Each item exposes a hover-only delete action. Pinned shortcuts at the top: Search, New chat, Browse web.

```vue
<template>
    <div class="border border-surface-200 dark:border-surface-700 rounded-lg overflow-hidden">
        <SidebarLayout class="min-h-192! relative!">
            <SidebarBackdrop v-if="isMobile && open" class="absolute!" />
            <Sidebar id="chat-history" :collapsible="isMobile ? 'offcanvas' : 'icon'" :overlay="isMobile" v-model:open="open" width="16rem">
                <SidebarSpacer />
                <SidebarAside>
                    <SidebarPanel>
                        <SidebarHeader>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <div class="flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-900 dark:bg-surface-0">
                                            <Sparkles class="size-3 text-surface-0 dark:text-surface-900" />
                                        </div>
                                        <span class="font-semibold text-sm">ChatGPT</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton>
                                        <Search />
                                        <span>Search</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                                <SidebarMenuItem>
                                    <SidebarMenuButton>
                                        <PenToSquare />
                                        <span>New chat</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                                <SidebarMenuItem>
                                    <SidebarMenuButton>
                                        <Globe />
                                        <span>Browse web</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarHeader>

                        <SidebarContent>
                            <SidebarGroup v-for="group in chatHistory" :key="group.label">
                                <SidebarGroupLabel>{{ group.label }}</SidebarGroupLabel>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem v-for="chat in group.chats" :key="chat.title">
                                            <SidebarMenuButton :isActive="!!chat.active">
                                                <span>{{ chat.title }}</span>
                                            </SidebarMenuButton>
                                            <SidebarMenuAction :showOnHover="true">
                                                <Trash />
                                            </SidebarMenuAction>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        </SidebarContent>

                        <SidebarFooter>
                            <SidebarMenu>
                                <SidebarMenuItem>
                                    <SidebarMenuButton class="p-1!">
                                        <Avatar label="JD" shape="circle" class="size-6 shrink-0 text-xs" />
                                        <span>John Doe</span>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            </SidebarMenu>
                        </SidebarFooter>
                    </SidebarPanel>
                </SidebarAside>
            </Sidebar>

            <SidebarMain>
                <header class="flex h-12 items-center gap-2 border-b border-surface-200 dark:border-surface-700 px-4">
                    <SidebarTrigger severity="secondary" target="chat-history" :text="true" size="small">
                        <SidebarIcon />
                    </SidebarTrigger>
                </header>
                <div class="flex-1 p-4 flex flex-col gap-4">
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 h-48"></div>
                    <div class="rounded-lg bg-surface-100 dark:bg-surface-800 flex-1"></div>
                </div>
            </SidebarMain>
        </SidebarLayout>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import Globe from '@primeicons/vue/globe';
import PenToSquare from '@primeicons/vue/pen-to-square';
import Search from '@primeicons/vue/search';
import SidebarIcon from '@primeicons/vue/sidebar';
import Sparkles from '@primeicons/vue/sparkles';
import Trash from '@primeicons/vue/trash';

const isMobile = ref(false);
const open = ref(true);
let mql = null;
let onMqlChange = null;

onMounted(() => {
    if (typeof window === 'undefined') return;

    mql = window.matchMedia('(max-width: 1023px)');
    isMobile.value = mql.matches;
    open.value = !isMobile.value;
    onMqlChange = (event) => {
        isMobile.value = event.matches;
        open.value = !event.matches;
    };
    mql.addEventListener('change', onMqlChange);
});

onBeforeUnmount(() => {
    if (mql && onMqlChange) {
        mql.removeEventListener('change', onMqlChange);
    }
});

const chatHistory = [
    {
        label: 'Today',
        chats: [
            {
                title: 'PrimeVue Sidebar component',
                active: true
            },
            { title: 'How to use Vue composables' },
            { title: 'Fix TypeScript generics issue' }
        ]
    },
    {
        label: 'Yesterday',
        chats: [{ title: 'Design system architecture' }, { title: 'Vue 3 new features overview' }, { title: 'CSS light-dark() function usage' }]
    },
    {
        label: 'Previous 7 days',
        chats: [{ title: 'Build a dashboard layout' }, { title: 'Tailwind v4 migration guide' }, { title: 'Node.js API authentication' }, { title: 'Monorepo setup with pnpm' }, { title: 'Deploy Nuxt to Vercel' }]
    },
    {
        label: 'Previous 30 days',
        chats: [{ title: 'GraphQL schema design' }, { title: 'WebSocket real-time updates' }, { title: 'PostgreSQL query optimization' }, { title: 'Docker compose for dev env' }]
    }
];
<\/script>
```

## Accessibility

Screen Reader Sidebar is a headless compound component and does not define a specific ARIA role by default. Use semantic elements such as nav or aside with aria-label or aria-labelledby to describe the purpose of the sidebar based on your layout. SidebarTrigger describes the relationship with the sidebar on its own: it exposes the current state with aria-expanded and adds aria-controls whenever the sidebar it controls has an id , which is rendered on the sidebar root. In layouts with multiple sidebars, provide the target prop to SidebarTrigger so it toggles and describes the intended sidebar. SidebarMenu renders a semantic list structure by default. Menu items are expected to contain interactive elements such as links or buttons. Collapsible SidebarMenuItem components add aria-expanded to their SidebarMenuButton automatically. Menu buttons are navigable as a single tree with the arrow keys, no matter how many SidebarMenu or SidebarGroup blocks they are split across. Navigation visits only the rows that are actually visible, so the children of a collapsed item are skipped. There is no roving tabindex, so every menu button also stays reachable with tab . A menu button that opens its own popup, marked with aria-haspopup , keeps its own key handling. Trigger Keyboard Support Key Function enter Toggles the sidebar. space Toggles the sidebar. Menu Keyboard Support Key Function tab Moves focus to the next focusable element in the sidebar or page tab sequence. shift + tab Moves focus to the previous focusable element in the sidebar or page tab sequence. enter Activates the focused link or button. For a collapsible menu item, toggles the submenu. space Activates the focused button. For a collapsible menu item, toggles the submenu. down arrow Moves focus to the next visible menu item. up arrow Moves focus to the previous visible menu item. right arrow Expands a collapsed menu item, or moves focus to its first child when it is already expanded. left arrow Collapses an expanded menu item, or moves focus to the parent menu item. home Moves focus to the first visible menu item. end Moves focus to the last visible menu item.

```vue
<template>
    <SidebarLayout>
        <Sidebar id="main-navigation" v-model:open="open" as="nav" aria-label="Main navigation">
            <SidebarAside>
                <SidebarPanel>
                    <SidebarContent>
                        <SidebarMenu>
                            <SidebarMenuItem>
                                <SidebarMenuButton as="a" href="/" :isActive="true">
                                    <Home />
                                    <span>Home</span>
                                </SidebarMenuButton>
                            </SidebarMenuItem>

                            <SidebarMenuItem :collapsible="true">
                                <SidebarMenuButton>
                                    <Folder />
                                    <span>Projects</span>
                                </SidebarMenuButton>
                                <SidebarMenuSub>
                                    <SidebarMenuSubItem>
                                        <SidebarMenuSubButton as="a" href="/projects/alpha">
                                            <span>Alpha</span>
                                        </SidebarMenuSubButton>
                                    </SidebarMenuSubItem>
                                </SidebarMenuSub>
                            </SidebarMenuItem>
                        </SidebarMenu>
                    </SidebarContent>
                </SidebarPanel>
            </SidebarAside>
        </Sidebar>

        <SidebarMain>
            <SidebarTrigger target="main-navigation" aria-label="Toggle navigation">
                <SidebarIcon />
            </SidebarTrigger>
        </SidebarMain>
    </SidebarLayout>
</template>
```

## Sidebar API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| id | string | - | Unique identifier; required when nested in a SidebarLayout to participate in registry. |
| side | "left" \| "right" | 'left' | Side of the viewport on which the sidebar is anchored. |
| variant | "sidebar" \| "floating" \| "inset" | 'sidebar' | Visual variant. |
| collapsible | "none" \| "offcanvas" \| "icon" | 'icon' | Collapse behavior. |
| overlay | boolean | false | Whether the panel renders as a floating overlay. |
| open | boolean | - | Controlled open state. Use with  `v-model:open`  or  `@update:open` . |
| openOnHover | boolean | false | When true, hovering the panel triggers expand/collapse. |
| hoverOpenDelay | number | 50 | Delay before expanding on hover, in ms. |
| hoverCloseDelay | number | 100 | Delay before collapsing after pointer leave, in ms. |
| dismissable | boolean | true | Whether clicking the backdrop dismisses the sidebar. |
| hideOnOutsideClick | boolean | true | When overlay is active, clicking inside the SidebarMain area collapses the sidebar. Clicks originating from a SidebarTrigger are excluded so opening via the trigger is not immediately undone. |
| width | string | '16rem' | Width of the expanded panel as a CSS length. |
| iconWidth | string | '3rem' | Width of the panel when collapsed in icon mode. |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Emits

| Name |Parameters |Description |
| --- | --- | --- |
| update:open | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| sidebar.border.color | --p-sidebar-border-color | Border color of root |
| sidebar.focus.ring.width | --p-sidebar-focus-ring-width | Focus ring width of root |
| sidebar.focus.ring.style | --p-sidebar-focus-ring-style | Focus ring style of root |
| sidebar.focus.ring.color | --p-sidebar-focus-ring-color | Focus ring color of root |
| sidebar.focus.ring.offset | --p-sidebar-focus-ring-offset | Focus ring offset of root |
| sidebar.focus.ring.shadow | --p-sidebar-focus-ring-shadow | Focus ring shadow of root |
| sidebar.layout.background | --p-sidebar-layout-background | Background of layout |
| sidebar.header.padding | --p-sidebar-header-padding | Padding of header |
| sidebar.header.gap | --p-sidebar-header-gap | Gap of header |
| sidebar.footer.padding | --p-sidebar-footer-padding | Padding of footer |
| sidebar.footer.gap | --p-sidebar-footer-gap | Gap of footer |
| sidebar.panel.background | --p-sidebar-panel-background | Background of panel |
| sidebar.panel.color | --p-sidebar-panel-color | Color of panel |
| sidebar.panel.floating.border.radius | --p-sidebar-panel-floating-border-radius | Border radius of floating variant panel |
| sidebar.panel.floating.shadow | --p-sidebar-panel-floating-shadow | Shadow of floating variant panel |
| sidebar.content.gap | --p-sidebar-content-gap | Gap of content |
| sidebar.aside.padding | --p-sidebar-aside-padding | Padding of aside |
| sidebar.group.padding | --p-sidebar-group-padding | Padding of group |
| sidebar.group.label.padding | --p-sidebar-group-label-padding | Padding of group label |
| sidebar.group.label.height | --p-sidebar-group-label-height | Height of group label |
| sidebar.group.label.border.radius | --p-sidebar-group-label-border-radius | Border radius of group label |
| sidebar.group.label.font.size | --p-sidebar-group-label-font-size | Font size of group label |
| sidebar.group.label.font.weight | --p-sidebar-group-label-font-weight | Font weight of group label |
| sidebar.group.label.color | --p-sidebar-group-label-color | Color of group label |
| sidebar.group.action.top | --p-sidebar-group-action-top | Top of group action |
| sidebar.group.action.right | --p-sidebar-group-action-right | Right of group action |
| sidebar.group.action.size | --p-sidebar-group-action-size | Size of group action |
| sidebar.group.action.border.radius | --p-sidebar-group-action-border-radius | Border radius of group action |
| sidebar.group.action.color | --p-sidebar-group-action-color | Color of group action |
| sidebar.group.action.focus.color | --p-sidebar-group-action-focus-color | Focus color of group action |
| sidebar.group.action.focus.background | --p-sidebar-group-action-focus-background | Focus background of group action |
| sidebar.group.action.icon.size | --p-sidebar-group-action-icon-size | Icon size of group action |
| sidebar.menu.gap | --p-sidebar-menu-gap | Gap of menu |
| sidebar.menu.button.padding | --p-sidebar-menu-button-padding | Padding of menu button |
| sidebar.menu.button.gap | --p-sidebar-menu-button-gap | Gap of menu button |
| sidebar.menu.button.height | --p-sidebar-menu-button-height | Height of menu button |
| sidebar.menu.button.border.radius | --p-sidebar-menu-button-border-radius | Border radius of menu button |
| sidebar.menu.button.font.size | --p-sidebar-menu-button-font-size | Font size of menu button |
| sidebar.menu.button.font.weight | --p-sidebar-menu-button-font-weight | Font weight of menu button |
| sidebar.menu.button.color | --p-sidebar-menu-button-color | Color of menu button |
| sidebar.menu.button.focus.background | --p-sidebar-menu-button-focus-background | Focus background of menu button |
| sidebar.menu.button.focus.color | --p-sidebar-menu-button-focus-color | Focus color of menu button |
| sidebar.menu.button.active.background | --p-sidebar-menu-button-active-background | Active background of menu button |
| sidebar.menu.button.active.color | --p-sidebar-menu-button-active-color | Active color of menu button |
| sidebar.menu.button.icon.only.width | --p-sidebar-menu-button-icon-only-width | Width of menu button in icon-only collapsible mode |
| sidebar.menu.button.with.action.padding.end | --p-sidebar-menu-button-with-action-padding-end | Padding end of menu button when it has a sibling menu action |
| sidebar.menu.button.icon.color | --p-sidebar-menu-button-icon-color | Icon color of menu button |
| sidebar.menu.button.icon.focus.color | --p-sidebar-menu-button-icon-focus-color | Icon focus color of menu button |
| sidebar.menu.button.icon.size | --p-sidebar-menu-button-icon-size | Icon size of menu button |
| sidebar.menu.action.top | --p-sidebar-menu-action-top | Top of menu action |
| sidebar.menu.action.right | --p-sidebar-menu-action-right | Right of menu action |
| sidebar.menu.action.width | --p-sidebar-menu-action-width | Width of menu action |
| sidebar.menu.action.border.radius | --p-sidebar-menu-action-border-radius | Border radius of menu action |
| sidebar.menu.action.color | --p-sidebar-menu-action-color | Color of menu action |
| sidebar.menu.action.focus.color | --p-sidebar-menu-action-focus-color | Focus color of menu action |
| sidebar.menu.action.focus.background | --p-sidebar-menu-action-focus-background | Focus background of menu action |
| sidebar.menu.action.icon.size | --p-sidebar-menu-action-icon-size | Icon size of menu action |
| sidebar.menu.badge.top | --p-sidebar-menu-badge-top | Top of menu badge |
| sidebar.menu.badge.right | --p-sidebar-menu-badge-right | Right of menu badge |
| sidebar.menu.badge.height | --p-sidebar-menu-badge-height | Height of menu badge |
| sidebar.menu.badge.min.width | --p-sidebar-menu-badge-min-width | Min width of menu badge |
| sidebar.menu.badge.border.radius | --p-sidebar-menu-badge-border-radius | Border radius of menu badge |
| sidebar.menu.badge.padding | --p-sidebar-menu-badge-padding | Padding of menu badge |
| sidebar.menu.badge.font.size | --p-sidebar-menu-badge-font-size | Font size of menu badge |
| sidebar.menu.badge.font.weight | --p-sidebar-menu-badge-font-weight | Font weight of menu badge |
| sidebar.menu.badge.background | --p-sidebar-menu-badge-background | Background of menu badge |
| sidebar.menu.badge.border.color | --p-sidebar-menu-badge-border-color | Border color of menu badge |
| sidebar.menu.badge.color | --p-sidebar-menu-badge-color | Color of menu badge |
| sidebar.menu.sub.padding.block | --p-sidebar-menu-sub-padding-block | Block padding of menu sub |
| sidebar.menu.sub.gap | --p-sidebar-menu-sub-gap | Gap of menu sub |
| sidebar.menu.sub.indent.margin | --p-sidebar-menu-sub-indent-margin | Margin of indented (non-collapsible) menu sub |
| sidebar.menu.sub.indent.padding | --p-sidebar-menu-sub-indent-padding | Padding of indented (non-collapsible) menu sub |
| sidebar.menu.sub.collapsible.indent | --p-sidebar-menu-sub-collapsible-indent | Left indent of collapsible menu sub |
| sidebar.menu.sub.collapsible.top.margin | --p-sidebar-menu-sub-collapsible-top-margin | Top margin of collapsible menu sub |
| sidebar.menu.sub.collapsible.border.radius | --p-sidebar-menu-sub-collapsible-border-radius | Border radius of collapsible menu sub |
| sidebar.menu.sub.button.padding | --p-sidebar-menu-sub-button-padding | Padding of menu sub button |
| sidebar.menu.sub.button.gap | --p-sidebar-menu-sub-button-gap | Gap of menu sub button |
| sidebar.menu.sub.button.height | --p-sidebar-menu-sub-button-height | Height of menu sub button |
| sidebar.menu.sub.button.border.radius | --p-sidebar-menu-sub-button-border-radius | Border radius of menu sub button |
| sidebar.menu.sub.button.font.size | --p-sidebar-menu-sub-button-font-size | Font size of menu sub button |
| sidebar.menu.sub.button.font.weight | --p-sidebar-menu-sub-button-font-weight | Font weight of menu sub button |
| sidebar.menu.sub.button.color | --p-sidebar-menu-sub-button-color | Color of menu sub button |
| sidebar.menu.sub.button.focus.background | --p-sidebar-menu-sub-button-focus-background | Focus background of menu sub button |
| sidebar.menu.sub.button.focus.color | --p-sidebar-menu-sub-button-focus-color | Focus color of menu sub button |
| sidebar.menu.sub.button.active.background | --p-sidebar-menu-sub-button-active-background | Active background of menu sub button |
| sidebar.menu.sub.button.active.color | --p-sidebar-menu-sub-button-active-color | Active color of menu sub button |
| sidebar.menu.sub.button.icon.color | --p-sidebar-menu-sub-button-icon-color | Icon color of menu sub button |
| sidebar.menu.sub.button.icon.focus.color | --p-sidebar-menu-sub-button-icon-focus-color | Icon focus color of menu sub button |
| sidebar.menu.sub.button.icon.size | --p-sidebar-menu-sub-button-icon-size | Icon size of menu sub button |
| sidebar.main.background | --p-sidebar-main-background | Background of main |
| sidebar.main.floating.background | --p-sidebar-main-floating-background | Floating background of main |
| sidebar.main.inset.background | --p-sidebar-main-inset-background | Inset background of main |
| sidebar.main.margin | --p-sidebar-main-margin | Margin of main |
| sidebar.main.border.radius | --p-sidebar-main-border-radius | Border radius of main |
| sidebar.main.shadow | --p-sidebar-main-shadow | Shadow of main |

## Sidebar Layout API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarLayoutPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-layout | Class name of the root element |

## Sidebar Aside API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarAsidePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-aside | Class name of the root element |

## Sidebar Panel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarPanelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-panel | Class name of the root element |

## Sidebar Header API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarHeaderPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-header | Class name of the root element |

## Sidebar Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-content | Class name of the root element |

## Sidebar Footer API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarFooterPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-footer | Class name of the root element |

## Sidebar Menu API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu | Class name of the root element |

## Sidebar Menu Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| collapsible | boolean | false | Marks the item as collapsible. |
| open | boolean | - | Controlled open state for the collapsible content. |
| defaultOpen | boolean | true | Initial open state for uncontrolled usage. |
| disabled | boolean | false | Disables the item; toggle is a no-op. |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Emits

| Name |Parameters |Description |
| --- | --- | --- |
| update:open | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-item | Class name of the root element |

## Sidebar Menu Sub API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuSubPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-sub | Class name of the root element |

## Sidebar Menu Sub Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuSubItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-sub-item | Class name of the root element |

## Sidebar Group API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-group | Class name of the root element |

## Sidebar Group Label API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarGroupLabelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-group-label | Class name of the root element |

## Sidebar Group Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarGroupContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-group-content | Class name of the root element |

## Sidebar Main API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMainPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-main | Class name of the root element |

## Sidebar Backdrop API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarBackdropPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-backdrop | Class name of the root element |

## Sidebar Spacer API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarSpacerPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-spacer | Class name of the root element |

## Sidebar Menu Button API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| isActive | boolean | false | Marks the button as the active menu entry. |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuButtonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-button | Class name of the root element |

## Sidebar Menu Sub Button API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| isActive | boolean | false | Marks the sub-button as the active entry. |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuSubButtonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-sub-button | Class name of the root element |

## Sidebar Menu Action API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| showOnHover | boolean | false | When true, the action is hidden until the parent menu item is hovered. |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuActionPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-action | Class name of the root element |

## Sidebar Menu Badge API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarMenuBadgePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-menu-badge | Class name of the root element |

## Sidebar Group Action API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarGroupActionPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-group-action | Class name of the root element |

## Sidebar Trigger API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| target | string | - | Target sidebar id to toggle when nested in SidebarLayout with multiple sidebars. |
| as | string \| object \| Function | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarTriggerPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-trigger | Class name of the root element |

## Sidebar Rail API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| object | - | The element or component to render. Defaults to a sensible HTML element. |
| asChild | boolean | false | When true, renders the slot content as the root element with merged props. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SidebarRailPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-sidebar-rail | Class name of the root element |

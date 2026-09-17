# SplitButton

SplitButton groups a set of commands in an overlay with a default command.

## Basic

SplitButton has a default action button and a collection of additional options defined by the model property based on MenuModel API.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <SplitButton label="Save" @click="save" :model="items" />
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Icons

The buttons and menuitems have support to display icons.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <SplitButton label="Save" @click="save" :model="items">
            <template #icon>
                <Check />
            </template>
            <template #dropdownicon>
                <Cog />
            </template>
        </SplitButton>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Cog from '@primeicons/vue/cog';
import PowerOff from '@primeicons/vue/power-off';
import Refresh from '@primeicons/vue/refresh';
import Times from '@primeicons/vue/times';
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        icon: Refresh,
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        icon: Times,
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        separator: true
    },
    {
        label: 'Quit',
        icon: PowerOff,
        command: () => {
            window.location.href = 'https://vuejs.org/';
        }
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Nested

SplitButton has a default action button and a collection of additional options defined by the model property based on MenuModel API.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <SplitButton label="Save" @click="save" :model="items" />
    </div>
</template>

<script setup>
import AlignCenter from '@primeicons/vue/align-center';
import AlignJustify from '@primeicons/vue/align-justify';
import AlignLeft from '@primeicons/vue/align-left';
import AlignRight from '@primeicons/vue/align-right';
import Bars from '@primeicons/vue/bars';
import Bookmark from '@primeicons/vue/bookmark';
import Calendar from '@primeicons/vue/calendar';
import CalendarMinus from '@primeicons/vue/calendar-minus';
import CalendarPlus from '@primeicons/vue/calendar-plus';
import CalendarTimes from '@primeicons/vue/calendar-times';
import ExternalLink from '@primeicons/vue/external-link';
import File from '@primeicons/vue/file';
import Filter from '@primeicons/vue/filter';
import Pencil from '@primeicons/vue/pencil';
import Plus from '@primeicons/vue/plus';
import PowerOff from '@primeicons/vue/power-off';
import Print from '@primeicons/vue/print';
import Trash from '@primeicons/vue/trash';
import User from '@primeicons/vue/user';
import UserMinus from '@primeicons/vue/user-minus';
import UserPlus from '@primeicons/vue/user-plus';
import Users from '@primeicons/vue/users';
import Video from '@primeicons/vue/video';
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'File',
        icon: File,
        items: [
            {
                label: 'New',
                icon: Plus,
                items: [
                    {
                        label: 'Bookmark',
                        icon: Bookmark
                    },
                    {
                        label: 'Video',
                        icon: Video
                    }
                ]
            },
            {
                label: 'Delete',
                icon: Trash
            },
            {
                separator: true
            },
            {
                label: 'Export',
                icon: ExternalLink
            }
        ]
    },
    {
        label: 'Edit',
        icon: Pencil,
        items: [
            {
                label: 'Left',
                icon: AlignLeft
            },
            {
                label: 'Right',
                icon: AlignRight
            },
            {
                label: 'Center',
                icon: AlignCenter
            },
            {
                label: 'Justify',
                icon: AlignJustify
            }
        ]
    },
    {
        label: 'Users',
        icon: User,
        items: [
            {
                label: 'New',
                icon: UserPlus
            },
            {
                label: 'Delete',
                icon: UserMinus
            },
            {
                label: 'Search',
                icon: Users,
                items: [
                    {
                        label: 'Filter',
                        icon: Filter,
                        items: [
                            {
                                label: 'Print',
                                icon: Print
                            }
                        ]
                    },
                    {
                        icon: Bars,
                        label: 'List'
                    }
                ]
            }
        ]
    },
    {
        label: 'Events',
        icon: Calendar,
        items: [
            {
                label: 'Edit',
                icon: Pencil,
                items: [
                    {
                        label: 'Save',
                        icon: CalendarPlus
                    },
                    {
                        label: 'Delete',
                        icon: CalendarMinus
                    }
                ]
            },
            {
                label: 'Archieve',
                icon: CalendarTimes,
                items: [
                    {
                        label: 'Remove',
                        icon: CalendarMinus
                    }
                ]
            }
        ]
    },
    {
        separator: true
    },
    {
        label: 'Quit',
        icon: PowerOff
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Severity

The severity property defines the variant of a button.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Primary" :model="items" @click="save"></SplitButton>
        <SplitButton label="Secondary" :model="items" @click="save" severity="secondary"></SplitButton>
        <SplitButton label="Success" :model="items" @click="save" severity="success"></SplitButton>
        <SplitButton label="Info" :model="items" @click="save" severity="info"></SplitButton>
        <SplitButton label="Warn" :model="items" @click="save" severity="warn"></SplitButton>
        <SplitButton label="Help" :model="items" @click="save" severity="help"></SplitButton>
        <SplitButton label="Danger" :model="items" @click="save" severity="danger"></SplitButton>
        <SplitButton label="Contrast" :model="items" @click="save" severity="contrast"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Disabled

When the disabled attribute is present, the element is uneditable and unfocused.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <SplitButton label="Save" @click="save" :model="items" disabled>
            <template #icon>
                <Plus />
            </template>
        </SplitButton>
    </div>
</template>

<script setup>
import Plus from '@primeicons/vue/plus';
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Raised

Raised buttons display a shadow to indicate elevation.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Primary" :model="items" @click="save" raised></SplitButton>
        <SplitButton label="Secondary" :model="items" @click="save" raised severity="secondary"></SplitButton>
        <SplitButton label="Success" :model="items" @click="save" raised severity="success"></SplitButton>
        <SplitButton label="Info" :model="items" @click="save" raised severity="info"></SplitButton>
        <SplitButton label="Warn" :model="items" @click="save" raised severity="warn"></SplitButton>
        <SplitButton label="Help" :model="items" @click="save" raised severity="help"></SplitButton>
        <SplitButton label="Danger" :model="items" @click="save" raised severity="danger"></SplitButton>
        <SplitButton label="Contrast" :model="items" @click="save" raised severity="contrast"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Rounded

Rounded buttons have a circular border radius.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Primary" :model="items" @click="save" rounded></SplitButton>
        <SplitButton label="Secondary" :model="items" @click="save" rounded severity="secondary"></SplitButton>
        <SplitButton label="Success" :model="items" @click="save" rounded severity="success"></SplitButton>
        <SplitButton label="Info" :model="items" @click="save" rounded severity="info"></SplitButton>
        <SplitButton label="Warn" :model="items" @click="save" rounded severity="warn"></SplitButton>
        <SplitButton label="Help" :model="items" @click="save" rounded severity="help"></SplitButton>
        <SplitButton label="Danger" :model="items" @click="save" rounded severity="danger"></SplitButton>
        <SplitButton label="Contrast" :model="items" @click="save" rounded severity="contrast"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Text

Text buttons are displayed as textual elements.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Primary" :model="items" @click="save" text></SplitButton>
        <SplitButton label="Secondary" :model="items" @click="save" text severity="secondary"></SplitButton>
        <SplitButton label="Success" :model="items" @click="save" text severity="success"></SplitButton>
        <SplitButton label="Info" :model="items" @click="save" text severity="info"></SplitButton>
        <SplitButton label="Warn" :model="items" @click="save" text severity="warn"></SplitButton>
        <SplitButton label="Help" :model="items" @click="save" text severity="help"></SplitButton>
        <SplitButton label="Danger" :model="items" @click="save" text severity="danger"></SplitButton>
        <SplitButton label="Contrast" :model="items" @click="save" text severity="contrast"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Raised Text

Text buttons can be displayed as raised as well for elevation.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Primary" :model="items" @click="save" raised text></SplitButton>
        <SplitButton label="Secondary" :model="items" @click="save" raised text severity="secondary"></SplitButton>
        <SplitButton label="Success" :model="items" @click="save" raised text severity="success"></SplitButton>
        <SplitButton label="Info" :model="items" @click="save" raised text severity="info"></SplitButton>
        <SplitButton label="Warn" :model="items" @click="save" raised text severity="warn"></SplitButton>
        <SplitButton label="Help" :model="items" @click="save" raised text severity="help"></SplitButton>
        <SplitButton label="Danger" :model="items" @click="save" raised text severity="danger"></SplitButton>
        <SplitButton label="Contrast" :model="items" @click="save" raised text severity="contrast"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Outlined

Outlined buttons display a border without a background initially.

```vue
<template>
    <div class="flex justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Primary" :model="items" @click="save" outlined></SplitButton>
        <SplitButton label="Secondary" :model="items" @click="save" outlined severity="secondary"></SplitButton>
        <SplitButton label="Success" :model="items" @click="save" outlined severity="success"></SplitButton>
        <SplitButton label="Info" :model="items" @click="save" outlined severity="info"></SplitButton>
        <SplitButton label="Warn" :model="items" @click="save" outlined severity="warn"></SplitButton>
        <SplitButton label="Help" :model="items" @click="save" outlined severity="help"></SplitButton>
        <SplitButton label="Danger" :model="items" @click="save" outlined severity="danger"></SplitButton>
        <SplitButton label="Contrast" :model="items" @click="save" outlined severity="contrast"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Sizes

SplitButton provides small and large sizes as alternatives to the standard.

```vue
<template>
    <div class="flex items-center justify-center flex-wrap gap-4">
        <Toast />
        <SplitButton label="Small" :model="items" @click="save" size="small"></SplitButton>
        <SplitButton label="Normal" :model="items" @click="save"></SplitButton>
        <SplitButton label="Large" :model="items" @click="save" size="large"></SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Template

Custom content inside a button is defined as children.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <SplitButton :model="items" @click="save" severity="contrast">
            <span class="flex items-center font-bold">
                <img alt="logo" src="https://primefaces.org/cdn/primevue/images/logo.svg" style="height: 1rem; margin-right: 0.5rem" />
                <span>PrimeVue</span>
            </span>
        </SplitButton>
    </div>
</template>

<script setup>
import { useToast } from "primevue/usetoast";
const toast = useToast();

const items = [
    {
        label: 'Update',
        command: () => {
            toast.add({ severity: 'success', summary: 'Updated', detail: 'Data Updated', life: 3000 });
        }
    },
    {
        label: 'Delete',
        command: () => {
            toast.add({ severity: 'warn', summary: 'Delete', detail: 'Data Deleted', life: 3000 });
        }
    },
    {
        label: 'Vue.js',
        url: 'https://vuejs.org/'
    },
    {
        separator: true
    },
    {
        label: 'Upload',
        route: '/fileupload'
    }
];

const save = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Data Saved', life: 3000 });
};
<\/script>
```

## Accessibility

Screen Reader SplitButton component renders two native button elements, main button uses the label property to define aria-label by default which can be customized with buttonProps . Dropdown button requires an explicit definition to describe it using menuButtonProps option and also includes aria-haspopup , aria-expanded for states along with aria-controls to define the relation between the popup and the button. The popup overlay uses menu role on the list and each action item has a menuitem role with an aria-label as the menuitem label. The id of the menu refers to the aria-controls of the dropdown button. Main Button Keyboard Support Key Function enter Activates the button. space Activates the button. Menu Button Keyboard Support Key Function enter space down arrow up arrow Opens the menu and moves focus to the first item. Menu Keyboard Support Key Function enter If menuitem has a submenu, opens the submenu otherwise activates the menuitem and closes all open overlays. space If menuitem has a submenu, opens the submenu otherwise activates the menuitem and closes all open overlays. escape If focus is inside a popup submenu, closes the submenu and moves focus to the root item of the closed submenu. down arrow Moves focus to the next menuitem within the submenu. up arrow Moves focus to the previous menuitem within the submenu. alt + up arrow Closes the popup, then moves focus to the target element. right arrow In nested mode if option is closed, opens the option otherwise moves focus to the first child option. left arrow In nested mode if option is open, closes the option otherwise moves focus to the parent option. home Moves focus to the first menuitem within the submenu. end Moves focus to the last menuitem within the submenu. any printable character Moves focus to the menuitem whose label starts with the characters being typed.

```vue
<template>
    <SplitButton :buttonProps="{'aria-label': 'Default Action'}" :menuButtonProps="{'aria-label': 'More Options'}" />
</template>
```

## Split Button API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| label | string | - | Text of the button. |
| icon | string | - | Name of the icon. |
| model | MenuItem[] | - | MenuModel instance to define the overlay items. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. Special keywords are 'body' for document body and 'self' for the element itself. |
| disabled | boolean | false | When present, it specifies that the element should be disabled. |
| fluid | boolean | null | Spans 100% width of the container when enabled. |
| class | any | - | Style class of the component. |
| style | any | - | Inline style of the component. |
| buttonProps | ButtonHTMLAttributes | - | Used to pass all properties of the HTMLButtonElement to the default button. |
| menuButtonProps | ButtonHTMLAttributes | - | Used to pass all properties of the HTMLButtonElement to the menu button. |
| menuButtonIcon | string | - | Name of the menu button icon. |
| dropdownIcon | string | - | Name of the menu button icon. |
| severity | any | - | Defines the style of the button. |
| raised | boolean | false | Add a shadow to indicate elevation. |
| rounded | boolean | false | Add a circular border radius to the button. |
| text | boolean | false | Add a textual class to the button without a background initially. |
| outlined | boolean | false | Add a border class without a background initially. |
| size | any | - | Defines the size of the button. |
| plain | boolean | false | Add a plain textual class to the button without a background initially. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SplitButtonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| pcButton | any | Used to pass attributes to the Button component. |
| pcDropdown | any | Used to pass attributes to the Button component. |
| pcMenu | any | Used to pass attributes to the TieredMenu component. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-splitbutton | Class name of the root element |
| p-splitbutton-button | Class name of the button element |
| p-splitbutton-dropdown | Class name of the dropdown element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| splitbutton.border.radius | --p-splitbutton-border-radius | Border radius of root |
| splitbutton.rounded.border.radius | --p-splitbutton-rounded-border-radius | Rounded border radius of root |
| splitbutton.raised.shadow | --p-splitbutton-raised-shadow | Raised shadow of root |

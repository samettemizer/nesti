# Dynamic Dialog

Dialogs can be created dynamically with any component as the content using a DialogService.

## Dialog Service

A single shared dialog instance is required in the application, ideal location would be defining it once at the main application template. A dynamic dialog is controlled via the DialogService that needs to be installed as an application plugin. The service is available with the useDialog function for Composition API or using the $dialog property of the application for Options API.

## Opening a Dialog

The open function of the DialogService is used to open a Dialog. First parameter is the component to load and second one is the configuration object to customize the Dialog. The component can also be loaded asynchronously, this approach is useful in conditional cases and to improve initial load times as well.

## Customization

DynamicDialog uses the Dialog component internally, visit dialog for more information about the available props.

```vue
import ProductListDemo from './ProductListDemo';
import { useDialog } from 'primevue/usedialog';

const dialog = useDialog();

const showProducts = () => {
    dialog.open(ProductListDemo, {
        props: {
            header: 'Product List',
            style: {
                width: '50vw',
            },
            breakpoints:{
                '960px': '75vw',
                '640px': '90vw'
            },
            modal: true
        }
    });
}
```

## Passing Data

Use the data property to pass parameters when opening a Dialog, the internal component can later access this data using dialogRef . Similarly when hiding a Dialog, any parameter passed to the close function is received from the onClose callback.

## Closing a Dialog

Most of the time, the requirement is returning a value from the dialog. The close function of the dialogRef is used for this purpose where the parameter passed will be available through the onClose callback at the caller. The dialogRef is injected to the component loaded by the dialog.

## Events

The emits object defines callbacks to handle events emitted by the component within the Dialog.

## Example

A sample implementation to demonstrate loading components asynchronously, nested content and passing data.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="showProducts">
            <Search />
            Select a Product
        </Button>
        <Toast />
        <DynamicDialog />
    </div>
</template>

<script setup>
import Search from '@primeicons/vue/search';
import { markRaw, defineAsyncComponent } from 'vue';
import { useDialog } from 'primevue/usedialog';
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
const ProductListDemo = defineAsyncComponent(() => import('./components/ProductListDemo.vue'));
const FooterDemo = defineAsyncComponent(() => import('./components/FooterDemo.vue'));

const dialog = useDialog();
const toast = useToast();

const showProducts = () => {
    const dialogRef = dialog.open(ProductListDemo, {
        props: {
            header: 'Product List',
            style: {
                width: '50vw',
            },
            breakpoints:{
                '960px': '75vw',
                '640px': '90vw'
            },
            modal: true
        },
        templates: {
            footer: markRaw(FooterDemo)
        },
        onClose: (options) => {
            const data = options.data;
            if (data) {
                const buttonType = data.buttonType;
                const summary_and_detail = buttonType ? { summary: 'No Product Selected', detail: \`Pressed '\${buttonType}' button\` } : { summary: 'Product Selected', detail: data.name };

                toast.add({ severity:'info', ...summary_and_detail, life: 3000 });
            }
        }
    });
}
<\/script>
```

## Accessibility

Visit accessibility section of dialog component for more information.

## Dynamic Dialog API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Theming

## Dialog API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| header | string | - | Title content of the dialog. |
| footer | string | - | Footer content of the dialog. |
| visible | boolean | false | Specifies the visibility of the dialog. |
| modal | boolean | false | Defines if background should be blocked when dialog is displayed. |
| contentStyle | any | - | Style of the content section. |
| contentClass | any | - | Style class of the content section. |
| contentProps | HTMLAttributes | - | Used to pass all properties of the HTMLDivElement to the overlay Dialog inside the component. |
| closable | boolean | true | Adds a close icon to the header to hide the dialog. |
| dismissableMask | boolean | false | Specifies if clicking the modal background should hide the dialog. |
| closeOnEscape | boolean | true | Specifies if pressing escape key should hide the dialog. |
| showHeader | boolean | true | Whether to show the header or not. |
| blockScroll | boolean | false | Whether background scroll should be blocked when dialog is visible. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| position | any | center | Position of the dialog. |
| maximizable | boolean | false | Whether the dialog can be displayed full screen. |
| breakpoints | DialogBreakpoints | - | Object literal to define widths per screen size. |
| draggable | boolean | true | Enables dragging to change the position using header. |
| keepInViewport | boolean | true | Keeps dialog in the viewport when dragging. |
| minX | number | 0. | Minimum value for the left coordinate of dialog in dragging. |
| minY | number | 0 | Minimum value for the top coordinate of dialog in dragging. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the dialog gets attached. |
| style | any | - | Style of the dynamic dialog. |
| closeIcon | string | - | Icon to display in the dialog close button. |
| maximizeIcon | string | - | Icon to display in the dialog maximize button when dialog is not maximized. |
| minimizeIcon | string | - | Icon to display in the dialog maximize button when dialog is minimized. |
| closeButtonProps | object | - | Used to pass all properties of the ButtonProps to the Button component. |
| maximizeButtonProps | object | - | Used to pass all properties of the ButtonProps to the Button component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DialogPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| header | DialogPassThroughOptionType<T> | Used to pass attributes to the header's DOM element. |
| title | DialogPassThroughOptionType<T> | Used to pass attributes to the header title's DOM element. |
| headerActions | DialogPassThroughOptionType<T> | Used to pass attributes to the header actions' DOM element. |
| pcMaximizeButton | any | Used to pass attributes to the maximize Button component. |
| pcCloseButton | any | Used to pass attributes to the close Button component. |
| content | DialogPassThroughOptionType<T> | Used to pass attributes to the content's DOM element. |
| footer | DialogPassThroughOptionType<T> | Used to pass attributes to the footer's DOM element. |
| mask | DialogPassThroughOptionType<T> | Used to pass attributes to the mask's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | DialogPassThroughTransitionType<T> | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-dialog-mask | Class name of the mask element |
| p-dialog | Class name of the root element |
| p-dialog-header | Class name of the header element |
| p-dialog-title | Class name of the title element |
| p-dialog-header-actions | Class name of the header actions element |
| p-dialog-maximize-button | Class name of the maximize button element |
| p-dialog-close-button | Class name of the close button element |
| p-dialog-content | Class name of the content element |
| p-dialog-footer | Class name of the footer element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| dialog.background | --p-dialog-background | Background of root |
| dialog.border.color | --p-dialog-border-color | Border color of root |
| dialog.color | --p-dialog-color | Color of root |
| dialog.border.radius | --p-dialog-border-radius | Border radius of root |
| dialog.shadow | --p-dialog-shadow | Shadow of root |
| dialog.header.padding | --p-dialog-header-padding | Padding of header |
| dialog.header.gap | --p-dialog-header-gap | Gap of header |
| dialog.title.font.size | --p-dialog-title-font-size | Font size of title |
| dialog.title.font.weight | --p-dialog-title-font-weight | Font weight of title |
| dialog.content.padding | --p-dialog-content-padding | Padding of content |
| dialog.footer.padding | --p-dialog-footer-padding | Padding of footer |
| dialog.footer.gap | --p-dialog-footer-gap | Gap of footer |

## Dialog Service Use Dialog API

## Dynamic Dialog Options API

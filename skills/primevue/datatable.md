# DataTable

DataTable displays data in tabular format.

## Basic

DataTable requires a collection to display along with Column components for the representation of the data.

```vue
<template>
    <div class="w-full">
        <DataTable :value="products" tableStyle="min-width: 50rem">
            <Column field="code" header="Code" />
            <Column field="name" header="Name" />
            <Column field="category" header="Category" />
            <Column field="quantity" header="Quantity" />
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsMini().then((data) => (products.value = data));
});

const products = ref();
<\/script>
```

## Size

Use the size property with small or large to adjust cell padding. Omit for the default size.

```vue
<template>
    <div>
        <div class="mb-4">
            <SelectButton v-model="selectedSize" :options="sizes" optionLabel="name" optionValue="value" dataKey="name" />
        </div>
        <DataTable :value="customers" :size="selectedSize" tableStyle="min-width: 50rem">
            <Column header="Name">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Representative">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <Avatar :image="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" shape="circle" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column header="Balance">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.balance.toLocaleString() }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

onMounted(() => {
    CustomerService.getCustomersSmall().then((data) => (customers.value = data.slice(0, 6)));
});

const customers = ref();
const selectedSize = ref(undefined);
const sizes = ref([
    { name: 'Small', value: 'small' },
    { name: 'Normal', value: undefined },
    { name: 'Large', value: 'large' }
]);

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};

<\/script>
```

## Grid Lines

Enabling showGridlines displays borders between cells.

```vue
<template>
    <div>
        <DataTable :value="customers" showGridlines tableStyle="min-width: 50rem">
            <Column field="name" header="Name">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Representative">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <Avatar :image="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" shape="circle" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="status" header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column field="balance" header="Balance">
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();

onMounted(() => {
    CustomerService.getCustomersSmall().then((data) => (customers.value = data.slice(0, 6)));
});

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

<\/script>
```

## Striped Rows

Alternating rows are displayed when stripedRows property is present.

```vue
<template>
    <div>
        <DataTable :value="customers" stripedRows tableStyle="min-width: 50rem">
            <Column field="name" header="Name">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Representative">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <Avatar :image="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" shape="circle" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="status" header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column field="balance" header="Balance">
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();

onMounted(() => {
    CustomerService.getCustomersSmall().then((data) => (customers.value = data.slice(0, 8)));
});

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

<\/script>
```

## Single

One row at a time. Clicking a different row replaces the previous selection.

```vue
<template>
    <div>
        <DataTable v-model:selection="selectedProduct" :value="products" selectionMode="single" dataKey="id" tableStyle="min-width: 50rem">
            <Column header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty"></Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 8)));
});

const products = ref();
const selectedProduct = ref();
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Multiple

Multiple rows without a dedicated column. Pair with metaKeySelection so Ctrl/Cmd + Click toggles rows and Shift + Click selects a range; a plain click still replaces the selection.

```vue
<template>
    <div>
        <div class="flex items-center justify-between gap-3 mb-3 p-3 rounded-md border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
            <div class="flex flex-wrap items-center gap-2">
                <span class="font-medium text-sm">Selected</span>
                <Badge :value="selectedProducts && selectedProducts.length > 0 ? selectedProducts.length.toString() : ''" :severity="selectedProducts && selectedProducts.length ? 'info' : 'secondary'" />
                <span v-if="selectedProducts && selectedProducts.length > 0" class="text-xs text-surface-500 dark:text-surface-400">
                    Total <span class="font-semibold text-surface-900 dark:text-surface-0">{{ '$' + totalValue }}</span>
                </span>
            </div>
            <div class="flex flex-wrap items-center gap-2">
                <Button severity="danger" size="small" variant="outlined" :disabled="!selectedProducts || !selectedProducts.length">
                    <Trash />
                    Delete
                </Button>
                <Button size="small" :disabled="!selectedProducts || !selectedProducts.length">
                    <ShoppingCart />
                    Add to cart
                </Button>
            </div>
        </div>
        <p class="mb-2 text-xs text-surface-500 dark:text-surface-400">Click to replace the selection. Ctrl/Cmd + Click to toggle a row, Shift + Click to select a range.</p>
        <DataTable v-model:selection="selectedProducts" :value="products" selectionMode="multiple" :metaKeySelection="true" dataKey="id" tableStyle="min-width: 50rem">
            <Column header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty"></Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';
import ShoppingCart from '@primeicons/vue/shopping-cart';
import Trash from '@primeicons/vue/trash';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 8)));
});

const products = ref();
const selectedProducts = ref();
const totalValue = computed(() => (selectedProducts.value || []).reduce((sum, p) => sum + p.price, 0));
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Checkbox

Checkbox-based multiple selection with a header select-all checkbox. Specify selectionMode as multiple on a Column to display a checkbox inside that column along with a header checkbox to toggle the whole dataset.

```vue
<template>
    <div>
        <div class="flex flex-wrap items-center justify-between gap-3 mb-3 p-3 rounded-md border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
            <div class="flex items-center gap-2">
                <span class="font-medium text-sm">Selected customers</span>
                <Badge :value="selectedCustomers && selectedCustomers.length > 0 ? selectedCustomers.length.toString() : ''" :severity="selectedCustomers && selectedCustomers.length ? 'info' : 'secondary'" />
            </div>
            <Button size="small" :disabled="!selectedCustomers || !selectedCustomers.length">
                <Envelope />
                Email selected
            </Button>
        </div>
        <DataTable v-model:selection="selectedCustomers" :value="customers" dataKey="id" tableStyle="min-width: 50rem">
            <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>
            <Column header="Name">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Representative">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <Avatar :image="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" shape="circle" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column header="Balance">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.balance.toLocaleString() }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';
import Envelope from '@primeicons/vue/envelope';

onMounted(() => {
    CustomerService.getCustomersSmall().then((data) => (customers.value = data.slice(0, 8)));
});

const customers = ref();
const selectedCustomers = ref();
const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';
        case 'unqualified':
            return 'danger';
        case 'negotiation':
            return 'warn';
        case 'new':
            return 'info';
        case 'renewal':
            return 'secondary';
        case 'proposal':
            return 'info';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Radio

Radio-based single selection. Specify selectionMode as single on a Column to display a radio button inside that column for selection.

```vue
<template>
    <div>
        <div class="flex flex-wrap items-center justify-between gap-3 mb-3 p-3 rounded-md border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
            <div class="flex flex-wrap items-center gap-2 text-sm">
                <span class="font-medium">Invoice recipient:</span>
                <span v-if="selectedCustomer" class="text-surface-900 dark:text-surface-0">
                    <strong>{{ selectedCustomer.name }}</strong> — {{ selectedCustomer.company }}
                </span>
                <span v-else class="text-surface-500 dark:text-surface-400">Pick a customer to assign</span>
            </div>
            <Button size="small" :disabled="!selectedCustomer">
                <UserPlus />
                Assign
            </Button>
        </div>
        <DataTable v-model:selection="selectedCustomer" :value="customers" dataKey="id" tableStyle="min-width: 50rem">
            <Column selectionMode="single" headerStyle="width: 3rem"></Column>
            <Column header="Name">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Representative">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <Avatar :image="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" shape="circle" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column header="Balance">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.balance.toLocaleString() }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';
import UserPlus from '@primeicons/vue/user-plus';

onMounted(() => {
    CustomerService.getCustomersSmall().then((data) => (customers.value = data.slice(0, 8)));
});

const customers = ref();
const selectedCustomer = ref();
const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';
        case 'unqualified':
            return 'danger';
        case 'negotiation':
            return 'warn';
        case 'new':
            return 'info';
        case 'renewal':
            return 'secondary';
        case 'proposal':
            return 'info';
        default:
            return 'secondary';
    }
};
<\/script>
```

## Keyboard

Arrow Up/Down moves focus between rows, Space or Enter toggles the focused row, and Shift + Arrow extends a range. Paired with selectionMode multiple and metaKeySelection , the whole flow is keyboard-driven.

```vue
<template>
    <div>
        <div class="flex flex-wrap items-center justify-between gap-3 mb-3 p-3 rounded-md border border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900">
            <span class="text-sm text-surface-500 dark:text-surface-400">
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">↑</kbd>{{ ' ' }}
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">↓</kbd> navigate,{{ ' ' }}
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">Space</kbd> /{{ ' ' }}
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">Enter</kbd> select,{{ ' ' }}
                <kbd class="px-1.5 py-0.5 text-xs rounded bg-surface-200 dark:bg-surface-700">Shift + ↑↓</kbd> range
            </span>
            <div class="flex items-center gap-2">
                <span class="text-sm font-medium">Selected</span>
                <Badge :value="selectedProducts && selectedProducts.length > 0 ? selectedProducts.length.toString() : ''" :severity="selectedProducts && selectedProducts.length ? 'info' : 'secondary'" />
            </div>
        </div>
        <DataTable v-model:selection="selectedProducts" :value="products" selectionMode="multiple" :metaKeySelection="true" dataKey="id" tableStyle="min-width: 50rem">
            <Column header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <span class="font-medium">{{ data.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty"></Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 8)));
});

const products = ref();
const selectedProducts = ref();
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Events

DataTable provides row-select and row-unselect events to listen selection events.

```vue
<template>
    <div>
        <DataTable v-model:selection="selectedProduct" :value="products" selectionMode="single" dataKey="code"
                @row-select="onRowSelect" @row-unselect="onRowUnselect" tableStyle="min-width: 50rem">
            <Column field="code" header="Code"></Column>
            <Column field="name" header="Name"></Column>
            <Column field="category" header="Category"></Column>
            <Column field="quantity" header="Quantity"></Column>
        </DataTable>
        <Toast />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsMini().then((data) => (products.value = data));
});

const products = ref();
const selectedProduct = ref();
const toast = useToast();
const onRowSelect = (event) => {
    toast.add({ severity: 'info', summary: 'Product Selected', detail: event.data.name, life: 3000 });
};
const onRowUnselect = (event) => {
    toast.add({ severity: 'info', summary: 'Product Unselected', detail: event.data.name, life: 3000 });
};
<\/script>
```

## Single

Clicking a column header cycles through ascending, descending, and unsorted. Add the sortable property to enable sorting on a column.

```vue
<template>
    <div>
        <DataTable :value="products" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Product" sortable>
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category" sortable>
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Quantity" sortable></Column>
            <Column field="price" header="Price" sortable>
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" sortable>
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 10)));
});

const products = ref();

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Multiple

Hold Ctrl/Cmd and click multiple column headers to sort by several fields at once. Set sortMode to multiple to enable.

```vue
<template>
    <div>
        <DataTable :value="products" sortMode="multiple" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Product" sortable>
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category" sortable>
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Quantity" sortable></Column>
            <Column field="price" header="Price" sortable>
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" sortable>
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 10)));
});

const products = ref();

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Presort

Apply an initial sort on mount using sortField and sortOrder . Headers stay interactive afterwards.

```vue
<template>
    <div>
        <DataTable :value="products" sortField="price" :sortOrder="-1" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Product" sortable>
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category" sortable>
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Quantity" sortable></Column>
            <Column field="price" header="Price" sortable>
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" sortable>
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 10)));
});

const products = ref();

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Multiple Presort

Apply an initial multi-column sort on mount by setting sortMode to multiple together with multiSortMeta . Each header keeps a badge with its sort order and stays interactive afterwards.

```vue
<template>
    <div>
        <DataTable :value="products" sortMode="multiple" :multiSortMeta="multiSortMeta" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Product" sortable>
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category" sortable>
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Quantity" sortable></Column>
            <Column field="price" header="Price" sortable>
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" sortable>
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 10)));
});

const products = ref();
const multiSortMeta = ref([
    { field: 'category', order: 1 },
    { field: 'price', order: -1 }
]);

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Removable

When removableSort is present, the third click removes the sorting from the column.

```vue
<template>
    <div>
        <DataTable :value="products" removableSort tableStyle="min-width: 50rem">
            <Column field="name" header="Product" sortable style="width: 30%">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category" sortable style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" sortable style="width: 10%"></Column>
            <Column field="price" header="Price" sortable style="width: 10%">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" sortable style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data));
});

const products = ref();

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};
<\/script>
```

## Basic

Pagination is enabled by setting paginator property to true and defining a rows property to specify the number of rows per page.

```vue
<template>
    <div>
        <DataTable :value="products" paginator :rows="5" :rowsPerPageOptions="[5, 10, 20]" tableStyle="min-width: 50rem">
            <Column header="Product" style="width: 30%">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column header="Category" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" style="width: 10%"></Column>
            <Column header="Price" style="width: 10%">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

onMounted(() => {
    ProductService.getProducts().then((data) => (products.value = data));
});
<\/script>
```

## Programmatic

Paginator can also be controlled via model using a binding to the first property where changes trigger a pagination.

```vue
<template>
    <div>
        <div class="mb-4 flex gap-1">
            <Button type="button" text :disabled="isFirstPage()" @click="prev">
                <ChevronLeft />
            </Button>
            <Button type="button" text @click="reset">
                <Refresh />
            </Button>
            <Button type="button" text :disabled="isLastPage()" @click="next">
                <ChevronRight />
            </Button>
        </div>
        <DataTable :value="products" paginator :rows="rows" :first="first"
                paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown CurrentPageReport"
                currentPageReportTemplate="Showing {first} to {last} of {totalRecords} entries"
                :rowsPerPageOptions="[10, 25, 50]" tableStyle="min-width: 50rem" @page="pageChange($event)">
            <Column header="Product" style="width: 30%">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" class="w-10 rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column header="Category" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" style="width: 10%"></Column>
            <Column header="Price" style="width: 10%">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { ProductService } from '@/service/ProductService';
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
import Refresh from '@primeicons/vue/refresh';

const products = ref();
const first = ref(0);
const rows = ref(10);

const next = () => {
    first.value = first.value + rows.value;
};

const prev = () => {
    first.value = first.value - rows.value;
};

const reset = () => {
    first.value = 0;
};

const pageChange = (event) => {
    first.value = event.first;
    rows.value = event.rows;
};

const isLastPage = () => {
    return products.value ? first.value + rows.value >= products.value.length : true;
};

const isFirstPage = () => {
    return products.value ? first.value === 0 : true;
};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

onMounted(() => {
    ProductService.getProducts().then((data) => (products.value = data));
});
<\/script>
```

## Vertical

A fixed scrollHeight enables vertical scrolling with a sticky header.

```vue
<template>
    <div>
        <DataTable :value="customers" scrollable scrollHeight="400px" tableStyle="min-width: 50rem">
            <Column field="name" header="Name">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column field="country.name" header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="representative.name" header="Representative">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <Avatar :image="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" shape="circle" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="status" header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column field="balance" header="Balance">
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => {
        customers.value = data;
    });
});

const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
<\/script>
```

## Horizontal

When the combined column widths exceed the container, the table scrolls horizontally. Give each column a minWidth so the columns don't squeeze.

```vue
<template>
    <div>
        <DataTable :value="customers" scrollable scrollHeight="400px">
            <Column field="id" header="Id" style="min-width: 6rem"></Column>
            <Column field="name" header="Name" style="min-width: 14rem">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column field="country.name" header="Country" style="min-width: 14rem"></Column>
            <Column field="date" header="Date" style="min-width: 12rem"></Column>
            <Column field="balance" header="Balance" style="min-width: 10rem">
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
            </Column>
            <Column field="company" header="Company" style="min-width: 14rem"></Column>
            <Column field="status" header="Status" style="min-width: 10rem">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column field="activity" header="Activity" style="min-width: 8rem">
                <template #body="{ data }">{{ data.activity }}%</template>
            </Column>
            <Column field="representative.name" header="Representative" style="min-width: 14rem"></Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => {
        customers.value = data;
    });
});

const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
<\/script>
```

## Flexible

scrollHeight="flex" lets the viewport grow and shrink with its flex parent — handy inside resizable dialogs or split layouts.

```vue
<template>
    <div class="flex justify-center">
        <Button type="button" @click="dialogVisible = true">Show Flex Scroll</Button>

        <Dialog v-model:visible="dialogVisible" header="Flex Scroll" :style="{ width: '75vw' }" maximizable modal appendTo="body" :contentStyle="{ height: '300px' }">
            <DataTable :value="customers" scrollable scrollHeight="flex" tableStyle="min-width: 50rem">
                <Column field="name" header="Name">
                    <template #body="{ data }">
                        <span class="font-medium">{{ data.name }}</span>
                    </template>
                </Column>
                <Column field="country.name" header="Country"></Column>
                <Column field="status" header="Status">
                    <template #body="{ data }">
                        <Tag :value="data.status" :severity="getSeverity(data.status)" />
                    </template>
                </Column>
                <Column field="balance" header="Balance">
                    <template #body="{ data }">
                        <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                    </template>
                </Column>
            </DataTable>
        </Dialog>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();
const dialogVisible = ref(false);

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => {
        customers.value = data;
    });
});

const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
<\/script>
```

## Frozen Columns

Certain columns can be frozen by using the frozen property of the column. In addition, alignFrozen is available to define whether the column should be fixed on the left or right.

```vue
<template>
    <div>
        <div class="mb-3">
            <ToggleButton v-model="balanceFrozen" onLabel="Balance" offLabel="Balance">
                <template #icon="{ value }">
                    <LockOpen v-if="value" />
                    <Lock v-else />
                </template>
            </ToggleButton>
        </div>

        <DataTable :value="customers" scrollable scrollHeight="400px">
            <Column field="name" header="Name" style="min-width: 200px" frozen>
                <template #body="{ data }">
                    <span class="font-semibold">{{ data.name }}</span>
                </template>
            </Column>
            <Column field="id" header="Id" style="min-width: 100px"></Column>
            <Column field="company" header="Company" style="min-width: 200px"></Column>
            <Column field="country.name" header="Country" style="min-width: 200px">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="date" header="Date" style="min-width: 200px"></Column>
            <Column field="status" header="Status" style="min-width: 200px">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column field="activity" header="Activity" style="min-width: 200px">
                <template #body="{ data }">{{ data.activity }}%</template>
            </Column>
            <Column field="representative.name" header="Representative" style="min-width: 200px"></Column>
            <Column field="balance" header="Balance" style="min-width: 200px" alignFrozen="right" :frozen="balanceFrozen">
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';
import Lock from '@primeicons/vue/lock';
import LockOpen from '@primeicons/vue/lock-open';

const customers = ref();
const balanceFrozen = ref(false);

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => {
        customers.value = data;
    });
});

const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
<\/script>
```

## Frozen Columns Multiple

Multiple columns can be frozen on either side of the table. Enable the frozen property on each column to pin it during horizontal scroll and use alignFrozen to fix a column to the left (default) or the right edge.

```vue
<template>
    <div>
        <DataTable :value="customers" scrollable scrollHeight="400px">
            <Column field="id" header="Id" style="min-width: 80px" frozen>
                <template #body="{ data }">
                    <span class="text-xs text-surface-500 dark:text-surface-400 tabular-nums">#{{ data.id }}</span>
                </template>
            </Column>
            <Column field="name" header="Name" style="min-width: 200px" frozen>
                <template #body="{ data }">
                    <span class="font-semibold">{{ data.name }}</span>
                </template>
            </Column>
            <Column field="country.name" header="Country" style="min-width: 200px" frozen>
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="company" header="Company" style="min-width: 220px"></Column>
            <Column field="representative.name" header="Representative" style="min-width: 200px"></Column>
            <Column field="date" header="Date" style="min-width: 200px"></Column>
            <Column field="activity" header="Activity" style="min-width: 200px">
                <template #body="{ data }">{{ data.activity }}%</template>
            </Column>
            <Column field="status" header="Status" style="min-width: 200px">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column field="balance" header="Balance" style="min-width: 180px" alignFrozen="right" frozen>
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => {
        customers.value = data;
    });
});

const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
<\/script>
```

## Frozen Rows

Frozen rows are used to fix certain rows while scrolling, this data is defined with the frozenValue property.

```vue
<template>
    <div>
        <DataTable :value="unlockedCustomers" :frozenValue="lockedCustomers" scrollable scrollHeight="400px" tableStyle="min-width: 50rem">
            <Column field="name" header="Name">
                <template #body="{ data, frozenRow }">
                    <span :class="frozenRow ? 'font-semibold' : 'font-medium'">{{ data.name }}</span>
                </template>
            </Column>
            <Column field="country.name" header="Country">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="representative.name" header="Representative"></Column>
            <Column field="status" header="Status">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <Column style="width: 4rem">
                <template #body="{ data, frozenRow, index }">
                    <Button type="button" :disabled="frozenRow ? false : lockedCustomers.length >= 2" text size="small" severity="secondary" :aria-label="frozenRow ? 'Unlock row' : 'Lock row'" @click="toggleLock(data, frozenRow, index)">
                        <template #icon>
                            <LockOpen v-if="frozenRow" />
                            <Lock v-else />
                        </template>
                    </Button>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';
import Lock from '@primeicons/vue/lock';
import LockOpen from '@primeicons/vue/lock-open';

const unlockedCustomers = ref();
const lockedCustomers = ref();

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => {
        lockedCustomers.value = [data[0]];
        unlockedCustomers.value = data.slice(1);
    });
});

const toggleLock = (data, frozen, index) => {
    if (frozen) {
        lockedCustomers.value = lockedCustomers.value.filter((c, i) => i !== index);
        unlockedCustomers.value.push(data);
    } else {
        unlockedCustomers.value = unlockedCustomers.value.filter((c, i) => i !== index);
        lockedCustomers.value.push(data);
    }

    unlockedCustomers.value.sort((val1, val2) => {
        return val1.id < val2.id ? -1 : 1;
    });
};

const getSeverity = (status) => {
    switch (status) {
        case 'qualified':
            return 'success';

        case 'unqualified':
            return 'danger';

        case 'negotiation':
            return 'warn';

        case 'new':
            return 'info';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';

        default:
            return 'secondary';
    }
};
<\/script>
```

## Row Expansion

Expand rows to show additional detail content. Use the row toggler callback to toggle expansion with expand/collapse icons.

```vue
<template>
    <div>
        <DataTable v-model:expandedRows="expandedRows" :value="products" dataKey="id" tableStyle="min-width: 50rem">
            <Column header="" style="width: 3rem">
                <template #body="{ data, rowTogglerCallback }">
                    <Button type="button" variant="text" severity="secondary" rounded iconOnly @click="rowTogglerCallback">
                        <ChevronDown v-if="expandedRows && expandedRows[data.id]" />
                        <ChevronRight v-else />
                    </Button>
                </template>
            </Column>
            <Column header="Product">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
            <template #expansion="{ data }">
                <div class="flex gap-4 p-4 bg-surface-50 dark:bg-surface-900">
                    <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="120" height="120" style="object-fit: cover; flex-shrink: 0" class="rounded-md shadow-md" />
                    <div class="flex flex-col gap-2 flex-1">
                        <h4 class="m-0 text-base font-semibold">{{ data.name }}</h4>
                        <div class="text-xs text-surface-500 dark:text-surface-400">SKU: {{ data.code }}</div>
                        <div class="flex items-center gap-2">
                            <Rating v-model="data.rating" readonly class="gap-0!" />
                            <span class="text-xs text-surface-500 dark:text-surface-400">({{ data.rating }}/5)</span>
                        </div>
                        <div class="flex items-center gap-6 text-sm">
                            <div>
                                <div class="text-xs text-surface-500 dark:text-surface-400">Category</div>
                                <div class="font-medium">{{ data.category }}</div>
                            </div>
                            <div>
                                <div class="text-xs text-surface-500 dark:text-surface-400">In stock</div>
                                <div class="font-medium">{{ data.quantity }} units</div>
                            </div>
                            <div>
                                <div class="text-xs text-surface-500 dark:text-surface-400">Price</div>
                                <div class="font-semibold">{{ '$' + data.price }}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </template>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';
import ChevronDown from '@primeicons/vue/chevron-down';
import ChevronRight from '@primeicons/vue/chevron-right';

const products = ref();
const expandedRows = ref({});

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return undefined;
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Cell

Cell editing is enabled by setting editMode as cell , defining input elements with editor slot of a Column and implementing cell-edit-complete to update the state.

```vue
<template>
    <div>
        <DataTable :value="products" dataKey="id" editMode="cell" @cell-edit-complete="onCellEditComplete"
            :pt="{
                table: { style: 'min-width: 50rem' },
                column: {
                    bodycell: ({ state }) => ({
                        class: [{ 'py-0!': state['d_editing'] }]
                    })
                }
            }"
        >
            <Column header="Image" style="width: 4rem">
                <template #body="{ data }">
                    <img :src="\`https://primefaces.org/cdn/primeng/images/demo/product/\${data.image}\`" :alt="data.name" width="40" height="40" class="rounded-md shadow" />
                </template>
            </Column>
            <Column field="name" header="Name" style="width: 30%">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
                <template #editor="{ data }">
                    <InputText v-model="data.name" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="category" header="Category" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
                <template #editor="{ data }">
                    <InputText v-model="data.category" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" style="width: 10%">
                <template #body="{ data }">
                    {{ data.quantity }}
                </template>
                <template #editor="{ data }">
                    <InputNumber v-model="data.quantity" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="price" header="Price" style="width: 15%">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
                <template #editor="{ data }">
                    <InputNumber v-model="data.price" mode="currency" currency="USD" locale="en-US" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
                <template #editor="{ data }">
                    <Select v-model="data.inventoryStatus" :options="statuses" optionLabel="label" optionValue="value" size="small" fluid />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();
const statuses = ref([
    { label: 'In Stock', value: 'INSTOCK' },
    { label: 'Low Stock', value: 'LOWSTOCK' },
    { label: 'Out of Stock', value: 'OUTOFSTOCK' }
]);

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const onCellEditComplete = (event) => {
    let { data, newValue, field } = event;

    switch (field) {
        case 'quantity':
        case 'price':
            if (isPositiveInteger(newValue)) data[field] = newValue;
            else event.preventDefault();
            break;

        default:
            if (newValue.trim().length > 0) data[field] = newValue;
            else event.preventDefault();
            break;
    }
};
const isPositiveInteger = (val) => {
    let str = String(val);

    str = str.trim();

    if (!str) {
        return false;
    }

    str = str.replace(/^0+/, '') || '0';
    var n = Math.floor(Number(str));

    return n !== Infinity && String(n) === str && n >= 0;
};
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return null;
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

<\/script>
```

## Cell & Selection

Cell editing composes with row selection. Clicks inside an editable cell start editing, while the checkbox column drives selection independently.

```vue
<template>
    <div>
        <div class="flex items-center gap-2 mb-3">
            <span class="text-sm font-medium">Selected</span>
            <Badge :value="String(selectedProducts ? selectedProducts.length : 0)" :severity="selectedProducts && selectedProducts.length ? 'info' : 'secondary'" />
        </div>
        <DataTable v-model:selection="selectedProducts" :value="products" dataKey="id" editMode="cell" @cell-edit-complete="onCellEditComplete"
            :pt="{
                table: { style: 'min-width: 50rem' },
                column: {
                    bodycell: ({ state }) => ({
                        class: [{ 'py-0!': state['d_editing'] }]
                    })
                }
            }"
        >
            <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>
            <Column header="Image" style="width: 4rem">
                <template #body="{ data }">
                    <img :src="\`https://primefaces.org/cdn/primeng/images/demo/product/\${data.image}\`" :alt="data.name" width="40" height="40" class="rounded-md shadow" />
                </template>
            </Column>
            <Column field="name" header="Name" style="width: 30%">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
                <template #editor="{ data }">
                    <InputText v-model="data.name" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="category" header="Category" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
                <template #editor="{ data }">
                    <InputText v-model="data.category" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" style="width: 10%">
                <template #body="{ data }">
                    {{ data.quantity }}
                </template>
                <template #editor="{ data }">
                    <InputNumber v-model="data.quantity" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="price" header="Price" style="width: 15%">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
                <template #editor="{ data }">
                    <InputNumber v-model="data.price" mode="currency" currency="USD" locale="en-US" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
                <template #editor="{ data }">
                    <Select v-model="data.inventoryStatus" :options="statuses" optionLabel="label" optionValue="value" size="small" fluid />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();
const selectedProducts = ref();
const statuses = ref([
    { label: 'In Stock', value: 'INSTOCK' },
    { label: 'Low Stock', value: 'LOWSTOCK' },
    { label: 'Out of Stock', value: 'OUTOFSTOCK' }
]);

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const onCellEditComplete = (event) => {
    let { data, newValue, field } = event;

    switch (field) {
        case 'quantity':
        case 'price':
            if (isPositiveInteger(newValue)) data[field] = newValue;
            else event.preventDefault();
            break;

        default:
            if (newValue.trim().length > 0) data[field] = newValue;
            else event.preventDefault();
            break;
    }
};
const isPositiveInteger = (val) => {
    let str = String(val);

    str = str.trim();

    if (!str) {
        return false;
    }

    str = str.replace(/^0+/, '') || '0';
    var n = Math.floor(Number(str));

    return n !== Infinity && String(n) === str && n >= 0;
};
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return null;
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};
<\/script>
```

## Row

Row editing is configured with setting editMode as row and defining editingRows with the v-model directive to hold the reference of the editing rows. Similarly with cell edit mode, defining input elements with editor slot of a Column and implementing row-edit-save are necessary to update the state. A special rowEditor Column displays the editing controls, and a dataKey is required to uniquely identify each row.

```vue
<template>
    <div>
        <DataTable v-model:editingRows="editingRows" :value="products" editMode="row" dataKey="id" @row-edit-save="onRowEditSave"
            :pt="{
                table: { style: 'min-width: 50rem' },
                column: {
                    bodycell: ({ state }) => ({
                        style: state['d_editing'] && 'padding-top: 0.75rem; padding-bottom: 0.75rem'
                    })
                }
            }"
        >
            <Column field="name" header="Product" style="width: 25%">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primeng/images/demo/product/\${data.image}\`" :alt="data.name" width="40" height="40" class="rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
                <template #editor="{ data, field }">
                    <InputText v-model="data[field]" fluid />
                </template>
            </Column>
            <Column field="category" header="Category" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
                <template #editor="{ data, field }">
                    <InputText v-model="data[field]" fluid />
                </template>
            </Column>
            <Column field="quantity" header="Qty" style="width: 10%">
                <template #editor="{ data, field }">
                    <InputNumber v-model="data[field]" fluid />
                </template>
            </Column>
            <Column field="price" header="Price" style="width: 10%">
                <template #body="{ data, field }">
                    <span class="font-semibold">{{ '$' + data[field] }}</span>
                </template>
                <template #editor="{ data, field }">
                    <InputNumber v-model="data[field]" mode="currency" currency="USD" locale="en-US" fluid />
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status" style="width: 20%">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
                <template #editor="{ data, field }">
                    <Select v-model="data[field]" :options="statuses" optionLabel="label" optionValue="value" placeholder="Select a Status" fluid />
                </template>
            </Column>
            <Column :rowEditor="true" style="width: 15%" bodyStyle="text-align:center"></Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();
const editingRows = ref([]);
const statuses = ref([
    { label: 'In Stock', value: 'INSTOCK' },
    { label: 'Low Stock', value: 'LOWSTOCK' },
    { label: 'Out of Stock', value: 'OUTOFSTOCK' }
]);

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const onRowEditSave = (event) => {
    let { newData, index } = event;

    products.value[index] = newData;
};
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return null;
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

<\/script>
```

## Subheader

Rows are grouped with the groupRowsBy property. When rowGroupMode is set as subheader , a header and footer can be displayed for each group. The content of a group header is provided with groupheader and footer with groupfooter slots.

```vue
<template>
    <div>
        <DataTable :value="customers" rowGroupMode="subheader" groupRowsBy="representative.name" sortMode="single"
                sortField="representative.name" :sortOrder="1" scrollable scrollHeight="400px" tableStyle="min-width: 50rem">
            <Column field="representative.name" header="Representative"></Column>
            <Column field="name" header="Name" style="min-width: 200px"></Column>
            <Column field="country" header="Country" style="min-width: 200px">
                <template #body="slotProps">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${slotProps.data.country.code}\`" style="width: 24px" />
                        <span>{{ slotProps.data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="company" header="Company" style="min-width: 200px"></Column>
            <Column field="status" header="Status" style="min-width: 200px">
                <template #body="slotProps">
                    <Tag :value="slotProps.data.status" :severity="getSeverity(slotProps.data.status)" />
                </template>
            </Column>
            <Column field="date" header="Date" style="min-width: 200px"></Column>
            <template #groupheader="slotProps">
                <div class="flex items-center gap-2">
                    <img :alt="slotProps.data.representative.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${slotProps.data.representative.image}\`" width="32" style="vertical-align: middle" />
                    <span>{{ slotProps.data.representative.name }}</span>
                </div>
            </template>
            <template #groupfooter="slotProps">
                <div class="flex justify-end font-bold w-full">Total Customers: {{ calculateCustomerTotal(slotProps.data.representative.name) }}</div>
            </template>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => (customers.value = data));
});

const customers = ref();
const calculateCustomerTotal = (name) => {
    let total = 0;

    if (customers.value) {
        for (let customer of customers.value) {
            if (customer.representative.name === name) {
                total++;
            }
        }
    }

    return total;
};
const getSeverity = (status) => {
    switch (status) {
        case 'unqualified':
            return 'danger';

        case 'qualified':
            return 'success';

        case 'new':
            return 'info';

        case 'negotiation':
            return 'warn';

        case 'renewal':
            return null;
    }
};
<\/script>
```

## RowSpan

When rowGroupMode is configured to be rowspan , the grouping column spans multiple rows.

```vue
<template>
    <div>
        <DataTable :value="customers" rowGroupMode="rowspan" groupRowsBy="representative.name" sortMode="single" sortField="representative.name" :sortOrder="1" tableStyle="min-width: 50rem">
            <Column header="#" headerStyle="width:3rem">
                <template #body="slotProps">
                    {{ slotProps.index + 1 }}
                </template>
            </Column>
            <Column field="representative.name" header="Representative" style="min-width: 200px">
                <template #body="slotProps">
                    <div class="flex items-center gap-2">
                        <img :alt="slotProps.data.representative.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${slotProps.data.representative.image}\`" width="32" style="vertical-align: middle" />
                        <span>{{ slotProps.data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="name" header="Name" style="min-width: 200px"></Column>
            <Column field="country" header="Country" style="min-width: 150px">
                <template #body="slotProps">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${slotProps.data.country.code}\`" style="width: 24px" />
                        <span>{{ slotProps.data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="company" header="Company" style="min-width: 200px"></Column>
            <Column field="status" header="Status" style="min-width: 100px">
                <template #body="slotProps">
                    <Tag :value="slotProps.data.status" :severity="getSeverity(slotProps.data.status)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => (customers.value = data));
});

const customers = ref();
const getSeverity = (status) => {
    switch (status) {
        case 'unqualified':
            return 'danger';

        case 'qualified':
            return 'success';

        case 'new':
            return 'info';

        case 'negotiation':
            return 'warn';

        case 'renewal':
            return null;
    }
};
<\/script>
```

## Expandable

When expandableRowGroups is present in subheader based row grouping, groups can be expanded and collapsed. State of the expansions are controlled using the expandedRows property and rowgroup-expand and rowgroup-collapse events.

```vue
<template>
    <div>
        <DataTable v-model:expandedRowGroups="expandedRowGroups" :value="customers" tableStyle="min-width: 50rem"
                expandableRowGroups rowGroupMode="subheader" groupRowsBy="representative.name" @rowgroup-expand="onRowGroupExpand" @rowgroup-collapse="onRowGroupCollapse"
                sortMode="single" sortField="representative.name" :sortOrder="1" :pt="{ rowToggleButton: { class: 'align-middle' } }">
            <template #groupheader="slotProps">
                <img :alt="slotProps.data.representative.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${slotProps.data.representative.image}\`" width="32" style="vertical-align: middle; display: inline-block" class="ml-2" />
                <span class="align-middle ml-2 font-bold leading-normal">{{ slotProps.data.representative.name }}</span>
            </template>
            <Column field="representative.name" header="Representative"></Column>
            <Column field="name" header="Name" style="width: 20%"></Column>
            <Column field="country" header="Country" style="width: 20%">
                <template #body="slotProps">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${slotProps.data.country.code}\`" style="width: 24px" />
                        <span>{{ slotProps.data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="company" header="Company" style="width: 20%"></Column>
            <Column field="status" header="Status" style="width: 20%">
                <template #body="slotProps">
                    <Tag :value="slotProps.data.status" :severity="getSeverity(slotProps.data.status)" />
                </template>
            </Column>
            <Column field="date" header="Date" style="width: 20%"></Column>
            <template #groupfooter="slotProps">
                <div class="flex justify-end font-bold w-full">Total Customers: {{ calculateCustomerTotal(slotProps.data.representative.name) }}</div>
            </template>
        </DataTable>
        <Toast />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { CustomerService } from '@/service/CustomerService';

onMounted(() => {
    CustomerService.getCustomersMedium().then((data) => (customers.value = data));
});

const customers = ref();
const expandedRowGroups = ref();
const toast = useToast();
const onRowGroupExpand = (event) => {
    toast.add({ severity: 'info', summary: 'Row Group Expanded', detail: 'Value: ' + event.data, life: 3000 });
};
const onRowGroupCollapse = (event) => {
    toast.add({ severity: 'success', summary: 'Row Group Collapsed', detail: 'Value: ' + event.data, life: 3000 });
};
const calculateCustomerTotal = (name) => {
    let total = 0;

    if (customers.value) {
        for (let customer of customers.value) {
            if (customer.representative.name === name) {
                total++;
            }
        }
    }

    return total;
};
const getSeverity = (status) => {
    switch (status) {
        case 'unqualified':
            return 'danger';

        case 'qualified':
            return 'success';

        case 'new':
            return 'info';

        case 'negotiation':
            return 'warn';

        case 'renewal':
            return null;
    }
};
<\/script>
```

## Fit Mode

Dragging a column takes width from the adjacent column so the total table width stays the same. Both demos enable showGridlines to make the effect visible.

```vue
<template>
    <div>
        <DataTable :value="products" showGridlines resizableColumns tableStyle="min-width: 50rem">
            <Column header="Product" style="width: 25%">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <span class="font-medium truncate">{{ data.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Category" style="width: 25%">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" style="width: 25%"></Column>
            <Column header="Price" style="width: 25%">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});
<\/script>
```

## Expand Mode

Dragging grows or shrinks the whole table; adjacent columns keep their widths. Usually paired with scrollable so the table can exceed its viewport.

```vue
<template>
    <div>
        <DataTable :value="products" showGridlines resizableColumns columnResizeMode="expand" scrollable scrollHeight="400px" tableStyle="min-width: 50rem">
            <Column header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <span class="font-medium truncate">{{ data.name }}</span>
                    </div>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty"></Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});
<\/script>
```

## Scrollable

Resizable columns can be combined with scrollable tables to keep headers and the resize handles aligned while the body scrolls.

```vue
<template>
    <div>
        <DataTable :value="customers" showGridlines scrollable scrollHeight="400px" resizableColumns tableStyle="min-width: 50rem">
            <Column field="name" header="Name"></Column>
            <Column field="country.name" header="Country"></Column>
            <Column field="company" header="Company"></Column>
            <Column field="representative.name" header="Representative"></Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { CustomerService } from '@/service/CustomerService';

const customers = ref();

onMounted(() => {
    CustomerService.getCustomersLarge().then((data) => (customers.value = data));
});
<\/script>
```

## Column

Drag and drop column headers to reorder columns.

```vue
<template>
    <div>
        <DataTable :value="products" reorderableColumns @column-reorder="onColReorder" tableStyle="min-width: 50rem">
            <Column field="name" header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <span class="font-medium">{{ data.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Quantity">
                <template #body="{ data }">
                    {{ data.quantity }}
                </template>
            </Column>
            <Column field="price" header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const products = ref();

const onColReorder = () => {};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return undefined;
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

<\/script>
```

## Row

Drag and drop rows to reorder data.

```vue
<template>
    <div>
        <DataTable :value="products" @row-reorder="onRowReorder" tableStyle="min-width: 50rem">
            <Column rowReorder headerStyle="width: 3rem" :reorderableColumn="false"></Column>
            <Column header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const products = ref();

const onRowReorder = (event) => {
    products.value = event.value;
};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return undefined;
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};
<\/script>
```

## Column Toggle

Show/hide columns dynamically.

```vue
<template>
    <div class="mb-3 flex items-center justify-end">
        <Button type="button" variant="outlined" severity="secondary" size="small" @click="toggle">
            <Cog />
            Columns
        </Button>
        <Popover ref="op" class="w-72" pt:content="p-0!">
            <div class="flex items-center justify-between gap-2 px-4 py-3 border-b border-surface-200 dark:border-surface-700">
                <span class="text-sm font-semibold">Columns</span>
                <Button type="button" variant="text" size="small" severity="secondary" @click="reset">
                    <Refresh />
                    Reset
                </Button>
            </div>
            <div class="py-2 max-h-80 overflow-auto" @dragover.prevent @drop="onColDrop">
                <div
                    v-for="(col, index) of columns"
                    :key="col.field"
                    class="flex items-center gap-2 px-3 py-1.5 mx-1 rounded-md cursor-move select-none transition"
                    :class="[
                        dragIndex === index ? 'opacity-40' : '',
                        dragOverIndex === index && dragIndex !== index ? 'bg-primary-50 dark:bg-primary-900/30 ring-1 ring-primary-400' : 'hover:bg-surface-100 dark:hover:bg-surface-800'
                    ]"
                    draggable="true"
                    @dragstart="onColDragStart(index)"
                    @dragover.prevent="onColDragOver(index)"
                    @dragend="onColDragEnd"
                >
                    <span class="flex text-surface-400 dark:text-surface-500"><Bars :size="14" /></span>
                    <Checkbox v-model="visibleFields" :value="col.field" :inputId="col.field" />
                    <label :for="col.field" class="text-sm cursor-pointer">{{ col.header }}</label>
                </div>
            </div>
        </Popover>
    </div>
    <DataTable :key="columnsKey" :value="products" tableStyle="min-width: 50rem">
        <Column v-for="col of visibleColumns" :key="col.field" :field="col.field" :header="col.header">
            <template #body="{ data }">
                <template v-if="col.field === 'name'">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
                <template v-else-if="col.field === 'category'">
                    <Tag :value="data.category" severity="secondary" />
                </template>
                <template v-else-if="col.field === 'quantity'">{{ data.quantity }}</template>
                <template v-else-if="col.field === 'price'">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
                <template v-else-if="col.field === 'rating'">{{ data.rating }}/5</template>
                <template v-else-if="col.field === 'inventoryStatus'">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </template>
        </Column>
    </DataTable>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';
import Bars from '@primeicons/vue/bars';
import Cog from '@primeicons/vue/cog';
import Refresh from '@primeicons/vue/refresh';

const initialColumns = [
    { field: 'name', header: 'Name' },
    { field: 'category', header: 'Category' },
    { field: 'quantity', header: 'Quantity' },
    { field: 'price', header: 'Price' },
    { field: 'rating', header: 'Rating' },
    { field: 'inventoryStatus', header: 'Status' }
];

const defaultVisibleFields = ['name', 'category', 'price', 'inventoryStatus'];

const op = ref();
const products = ref();
const columns = ref([...initialColumns]);
const visibleFields = ref([...defaultVisibleFields]);
const dragIndex = ref(null);
const dragOverIndex = ref(null);

const visibleColumns = computed(() => columns.value.filter((col) => visibleFields.value.includes(col.field)));
const columnsKey = computed(() => visibleColumns.value.map((col) => col.field).join('-'));

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 6)));
});

const toggle = (event) => {
    op.value.toggle(event);
};

const onColDragStart = (index) => {
    dragOverIndex.value = index;
    requestAnimationFrame(() => (dragIndex.value = index));
};

const onColDragOver = (index) => {
    if (index !== dragIndex.value) dragOverIndex.value = index;
};

const onColDrop = () => {
    const from = dragIndex.value;
    const to = dragOverIndex.value;

    if (from !== null && to !== null && from !== to) {
        const cols = [...columns.value];
        const [moved] = cols.splice(from, 1);

        cols.splice(to, 0, moved);
        columns.value = cols;
    }

    onColDragEnd();
};

const onColDragEnd = () => {
    dragIndex.value = null;
    dragOverIndex.value = null;
};

const reset = () => {
    columns.value = [...initialColumns];
    visibleFields.value = [...defaultVisibleFields];
};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Basic

Multi-level headers with rowspan and colspan.

```vue
<template>
    <DataTable :value="sales" tableStyle="min-width: 50rem" showGridlines>
        <ColumnGroup type="header">
            <Row>
                <Column header="Product" :rowspan="2" />
                <Column header="Sale Rate" :colspan="2" headerStyle="text-align: center" />
                <Column header="Profits" :colspan="2" headerStyle="text-align: center" />
            </Row>
            <Row>
                <Column header="Last Year" />
                <Column header="This Year" />
                <Column header="Last Year" />
                <Column header="This Year" />
            </Row>
        </ColumnGroup>
        <Column field="product">
            <template #body="{ data }">
                <span class="font-medium">{{ data.product }}</span>
            </template>
        </Column>
        <Column field="lastYearSale">
            <template #body="{ data }">{{ data.lastYearSale }}%</template>
        </Column>
        <Column field="thisYearSale">
            <template #body="{ data }">
                <div class="inline-flex items-center gap-1">
                    <span>{{ data.thisYearSale }}%</span>
                    <ArrowUp v-if="data.thisYearSale >= data.lastYearSale" class="w-3 h-3 text-green-500" />
                    <ArrowDown v-else class="w-3 h-3 text-red-500" />
                </div>
            </template>
        </Column>
        <Column field="lastYearProfit">
            <template #body="{ data }">{{ formatCurrency(data.lastYearProfit) }}</template>
        </Column>
        <Column field="thisYearProfit">
            <template #body="{ data }">
                <Tag :value="formatCurrency(data.thisYearProfit)" :severity="data.thisYearProfit >= data.lastYearProfit ? 'success' : 'danger'" />
            </template>
        </Column>
        <ColumnGroup type="footer">
            <Row>
                <Column footer="Totals" :colspan="3" footerStyle="text-align: right" />
                <Column :footer="formatCurrency(lastYearTotal)" />
                <Column :footer="formatCurrency(thisYearTotal)" />
            </Row>
        </ColumnGroup>
    </DataTable>
</template>

<script setup>
import { ref, computed } from 'vue';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';

const sales = ref([
    { product: 'Bamboo Watch', lastYearSale: 51, thisYearSale: 40, lastYearProfit: 54406, thisYearProfit: 43342 },
    { product: 'Black Watch', lastYearSale: 83, thisYearSale: 9, lastYearProfit: 423132, thisYearProfit: 312122 },
    { product: 'Blue Band', lastYearSale: 38, thisYearSale: 5, lastYearProfit: 12321, thisYearProfit: 8500 },
    { product: 'Blue T-Shirt', lastYearSale: 49, thisYearSale: 22, lastYearProfit: 745232, thisYearProfit: 650323 },
    { product: 'Bracelet', lastYearSale: 17, thisYearSale: 79, lastYearProfit: 643242, thisYearProfit: 500332 }
]);

const formatCurrency = (value) => {
    return value != null ? '$' + value.toLocaleString() : '';
};

const lastYearTotal = computed(() => sales.value.reduce((total, sale) => total + sale.lastYearProfit, 0));
const thisYearTotal = computed(() => sales.value.reduce((total, sale) => total + sale.thisYearProfit, 0));
<\/script>
```

## Filter & Sort

Sort and filter work on any leaf header cell in a grouped layout. Add sortable with a field to the leaf header columns and a filter row below them with the filter templates.

```vue
<template>
    <DataTable v-model:filters="filters" :value="sales" filterDisplay="row" removableSort showGridlines tableStyle="min-width: 50rem">
        <ColumnGroup type="header">
            <Row>
                <Column header="Product" field="product" sortable :rowspan="2" />
                <Column header="Sale Rate" :colspan="2" headerStyle="text-align: center" />
                <Column header="Profits" :colspan="2" headerStyle="text-align: center" />
            </Row>
            <Row>
                <Column header="Last Year" field="lastYearSale" sortable />
                <Column header="This Year" field="thisYearSale" sortable />
                <Column header="Last Year" field="lastYearProfit" sortable />
                <Column header="This Year" field="thisYearProfit" sortable />
            </Row>
        </ColumnGroup>
        <Column field="product">
            <template #body="{ data }">
                <span class="font-medium">{{ data.product }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
                <InputText v-model="filterModel.value" size="small" type="text" @input="filterCallback()" placeholder="Search" fluid />
            </template>
        </Column>
        <Column field="lastYearSale">
            <template #body="{ data }">{{ data.lastYearSale }}%</template>
        </Column>
        <Column field="thisYearSale">
            <template #body="{ data }">
                <div class="inline-flex items-center gap-1">
                    <span>{{ data.thisYearSale }}%</span>
                    <ArrowUp v-if="data.thisYearSale >= data.lastYearSale" class="w-3 h-3 text-green-500" />
                    <ArrowDown v-else class="w-3 h-3 text-red-500" />
                </div>
            </template>
            <template #filter="{ filterModel, filterCallback }">
                <InputText v-model="filterModel.value" size="small" type="number" @input="filterCallback()" placeholder="&ge;" fluid />
            </template>
        </Column>
        <Column field="lastYearProfit">
            <template #body="{ data }">{{ formatCurrency(data.lastYearProfit) }}</template>
        </Column>
        <Column field="thisYearProfit">
            <template #body="{ data }">
                <Tag :value="formatCurrency(data.thisYearProfit)" :severity="data.thisYearProfit >= data.lastYearProfit ? 'success' : 'danger'" />
            </template>
        </Column>
    </DataTable>
</template>

<script setup>
import { ref } from 'vue';
import { FilterMatchMode } from '@primevue/core/api';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';

const sales = ref([
    { product: 'Bamboo Watch', lastYearSale: 51, thisYearSale: 40, lastYearProfit: 54406, thisYearProfit: 43342 },
    { product: 'Black Watch', lastYearSale: 83, thisYearSale: 9, lastYearProfit: 423132, thisYearProfit: 312122 },
    { product: 'Blue Band', lastYearSale: 38, thisYearSale: 5, lastYearProfit: 12321, thisYearProfit: 8500 },
    { product: 'Blue T-Shirt', lastYearSale: 49, thisYearSale: 22, lastYearProfit: 745232, thisYearProfit: 650323 },
    { product: 'Bracelet', lastYearSale: 17, thisYearSale: 79, lastYearProfit: 643242, thisYearProfit: 500332 }
]);
const filters = ref({
    product: { value: null, matchMode: FilterMatchMode.CONTAINS },
    thisYearSale: { value: null, matchMode: FilterMatchMode.GREATER_THAN_OR_EQUAL_TO }
});

const formatCurrency = (value) => {
    return value != null ? '$' + value.toLocaleString() : '';
};
<\/script>
```

## Basic

Data filtering is enabled by defining the filters model referring to a DataTableFilterMeta instance and enabling the filterDisplay as row . Each column to filter also requires a filter template to customize the filtering with your own UI. This template receives a filterModel and filterCallback to build your own filter element. The optional global filtering searches the data against a single value that is bound to the global key of the filters object. The fields to search against are defined with the globalFilterFields .

```vue
<template>
    <div class="mb-3 flex justify-end">
        <IconField>
            <InputIcon>
                <Search />
            </InputIcon>
            <InputText v-model="filters['global'].value" size="small" placeholder="Keyword Search" />
        </IconField>
    </div>
    <DataTable v-model:filters="filters" :value="customers" dataKey="id" filterDisplay="row" :globalFilterFields="['name', 'country', 'status']" tableStyle="min-width: 50rem">
        <template #empty> No customers found. </template>
        <Column field="name" header="Name" :showFilterMenu="false" style="width: 25%">
            <template #body="{ data }">
                <span class="font-medium">{{ data.name }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
                <InputText v-model="filterModel.value" size="small" type="text" @input="filterCallback()" placeholder="Search name..." />
            </template>
        </Column>
        <Column field="country" header="Country" :showFilterMenu="false" style="width: 20%">
            <template #filter="{ filterModel, filterCallback }">
                <InputText v-model="filterModel.value" size="small" type="text" @input="filterCallback()" placeholder="Search country..." />
            </template>
        </Column>
        <Column field="status" header="Status" :showFilterMenu="false" style="width: 20%">
            <template #body="{ data }">
                <Tag :value="data.status" :severity="getSeverity(data.status)" />
            </template>
            <template #filter="{ filterModel, filterCallback }">
                <Select v-model="filterModel.value" @change="filterCallback()" :options="statusOptions" optionLabel="label" optionValue="value" placeholder="Any" size="small" style="min-width: 12rem" />
            </template>
        </Column>
        <Column field="balance" header="Balance" style="width: 20%">
            <template #body="{ data }">
                <span class="font-semibold">{{ '$' + data.balance.toLocaleString() }}</span>
            </template>
        </Column>
        <Column field="verified" header="Verified" style="width: 15%">
            <template #body="{ data }">
                <Tag v-if="data.verified" value="Verified" severity="success" />
                <Tag v-else value="—" severity="secondary" />
            </template>
        </Column>
    </DataTable>
</template>

<script setup>
import { ref } from 'vue';
import { FilterMatchMode } from '@primevue/core/api';
import Search from '@primeicons/vue/search';

const customers = ref([
    { id: 1, name: 'Amy Elsner', country: 'Germany', status: 'unqualified', verified: false, balance: 9702 },
    { id: 2, name: 'Anna Fali', country: 'France', status: 'qualified', verified: true, balance: 12500 },
    { id: 3, name: 'Asiya Javayant', country: 'India', status: 'new', verified: false, balance: 8300 },
    { id: 4, name: 'Bernardo Dominic', country: 'USA', status: 'renewal', verified: true, balance: 24100 },
    { id: 5, name: 'Elwin Sharvill', country: 'UK', status: 'qualified', verified: true, balance: 16200 },
    { id: 6, name: 'Ioni Bowcher', country: 'Brazil', status: 'unqualified', verified: false, balance: 4200 },
    { id: 7, name: 'Ivan Magalhaes', country: 'Brazil', status: 'new', verified: true, balance: 18700 },
    { id: 8, name: 'Onyama Limba', country: 'Nigeria', status: 'qualified', verified: false, balance: 29300 },
    { id: 9, name: 'Stephen Shaw', country: 'UK', status: 'negotiation', verified: true, balance: 15800 },
    { id: 10, name: 'Xuxue Feng', country: 'China', status: 'renewal', verified: true, balance: 44500 }
]);
const statusOptions = ref([
    { label: 'All', value: '' },
    { label: 'Unqualified', value: 'unqualified' },
    { label: 'Qualified', value: 'qualified' },
    { label: 'New', value: 'new' },
    { label: 'Negotiation', value: 'negotiation' },
    { label: 'Renewal', value: 'renewal' }
]);
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    country: { value: null, matchMode: FilterMatchMode.CONTAINS },
    status: { value: null, matchMode: FilterMatchMode.EQUALS }
});

const getSeverity = (status) => {
    switch (status) {
        case 'unqualified':
            return 'danger';

        case 'qualified':
            return 'success';

        case 'new':
            return 'info';

        case 'negotiation':
            return 'warn';

        case 'renewal':
            return 'secondary';
    }
};
<\/script>
```

## Advanced

filterDisplay="menu" swaps the inline input for a trigger icon that opens a popover. Advanced fields expose a match mode per constraint with Apply and Clear actions, and the Name column stacks up to three rules joined by an AND/OR operator, while simpler fields provide a single editor.

```vue
<template>
    <div>
        <div class="mb-3 flex items-center justify-between gap-3">
            <Button type="button" variant="outlined" size="small" @click="clearFilter()">
                <FilterSlash />
                Clear Filters
            </Button>
            <IconField iconPosition="left">
                <InputIcon>
                    <Search />
                </InputIcon>
                <InputText v-model="filters['global'].value" type="text" placeholder="Keyword Search" />
            </IconField>
        </div>
        <DataTable v-model:filters="filters" :value="customers" dataKey="id" :rows="10" :rowsPerPageOptions="[10, 25, 50]" :loading="loading"
                paginator filterDisplay="menu" :globalFilterFields="['name', 'country.name', 'representative.name', 'status']">
            <template #empty> No customers found. </template>
            <Column field="name" header="Name" :maxConstraints="3" style="min-width: 14rem">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
                <template #filter="{ filterModel }">
                    <InputText v-model="filterModel.value" type="text" placeholder="Search by name" />
                </template>
            </Column>
            <Column header="Country" filterField="country.name" :showFilterOperator="false" :showAddButton="false" style="min-width: 12rem">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 20px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
                <template #filter="{ filterModel }">
                    <InputText v-model="filterModel.value" type="text" placeholder="Search by country" />
                </template>
            </Column>
            <Column header="Agent" filterField="representative.name" :showFilterMatchModes="false" :showFilterOperator="false" :showAddButton="false" :filterMenuStyle="{ minWidth: '16rem' }" style="min-width: 14rem">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img :alt="data.representative.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" width="32" class="rounded-full" />
                        <span class="text-sm">{{ data.representative.name }}</span>
                    </div>
                </template>
                <template #filter="{ filterModel }">
                    <Select v-model="filterModel.value" :options="representatives" optionLabel="name" optionValue="name" placeholder="Any agent" filter showClear class="w-full">
                        <template #value="slotProps">
                            <div v-if="slotProps.value" class="flex items-center gap-2">
                                <img :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${getRepImage(slotProps.value)}\`" width="24" class="rounded-full" />
                                <span>{{ slotProps.value }}</span>
                            </div>
                            <span v-else>{{ slotProps.placeholder }}</span>
                        </template>
                        <template #option="slotProps">
                            <div class="flex items-center gap-2">
                                <img :alt="slotProps.option.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${slotProps.option.image}\`" width="32" class="rounded-full" />
                                <span>{{ slotProps.option.name }}</span>
                            </div>
                        </template>
                    </Select>
                </template>
            </Column>
            <Column header="Date" filterField="date" dataType="date" :showFilterOperator="false" :showAddButton="false" style="min-width: 12rem">
                <template #body="{ data }">
                    {{ formatDate(data.date) }}
                </template>
                <template #filter="{ filterModel }">
                    <DatePicker v-model="filterModel.value" dateFormat="mm/dd/yy" placeholder="mm/dd/yyyy" />
                </template>
            </Column>
            <Column header="Balance" filterField="balance" dataType="numeric" :showFilterOperator="false" :showAddButton="false" style="min-width: 12rem">
                <template #body="{ data }">
                    <span class="font-semibold">{{ formatCurrency(data.balance) }}</span>
                </template>
                <template #filter="{ filterModel }">
                    <InputNumber v-model="filterModel.value" mode="currency" currency="USD" locale="en-US" placeholder="Enter amount" />
                </template>
            </Column>
            <Column header="Status" field="status" :showFilterMatchModes="false" :showFilterOperator="false" :showAddButton="false" :filterMenuStyle="{ width: '14rem' }" style="min-width: 12rem">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
                <template #filter="{ filterModel }">
                    <Select v-model="filterModel.value" :options="statuses" optionLabel="label" optionValue="value" placeholder="Select One" showClear class="w-full">
                        <template #value="slotProps">
                            <Tag v-if="slotProps.value" :value="slotProps.value" :severity="getSeverity(slotProps.value)" />
                            <span v-else>{{ slotProps.placeholder }}</span>
                        </template>
                        <template #option="slotProps">
                            <Tag :value="slotProps.option.value" :severity="getSeverity(slotProps.option.value)" />
                        </template>
                    </Select>
                </template>
            </Column>
            <Column field="activity" header="Activity" :showFilterMatchModes="false" :showFilterOperator="false" :showAddButton="false" :filterMenuStyle="{ minWidth: '16rem' }" style="min-width: 14rem">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <div class="flex-1 h-1.5 rounded-full bg-surface-200 dark:bg-surface-700 overflow-hidden">
                            <div class="h-full bg-primary-500 rounded-full" :style="{ width: data.activity + '%' }"></div>
                        </div>
                        <span class="text-xs text-surface-500 dark:text-surface-400 tabular-nums">{{ data.activity }}%</span>
                    </div>
                </template>
                <template #filter="{ filterModel }">
                    <div class="px-3 pt-4 pb-2">
                        <Slider v-model="filterModel.value" range></Slider>
                    </div>
                    <div class="flex items-center justify-between px-3">
                        <span>{{ filterModel.value ? filterModel.value[0] : 0 }}%</span>
                        <span>{{ filterModel.value ? filterModel.value[1] : 100 }}%</span>
                    </div>
                </template>
            </Column>
            <Column field="verified" header="Verified" dataType="boolean" :showFilterMatchModes="false" :showFilterOperator="false" :showAddButton="false" style="min-width: 12rem">
                <template #body="{ data }">
                    <Tag v-if="data.verified" value="Verified" severity="success" />
                    <Tag v-else value="—" severity="secondary" />
                </template>
                <template #filter="{ filterModel }">
                    <SelectButton v-model="filterModel.value" :options="verifiedOptions" optionLabel="label" optionValue="value" :allowEmpty="false" size="small" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';
import { FilterMatchMode, FilterOperator } from '@primevue/core/api';
import FilterSlash from '@primeicons/vue/filter-slash';
import Search from '@primeicons/vue/search';

const customers = ref();
const filters = ref();
const representatives = ref([
    { name: 'Amy Elsner', image: 'amyelsner.png' },
    { name: 'Anna Fali', image: 'annafali.png' },
    { name: 'Asiya Javayant', image: 'asiyajavayant.png' },
    { name: 'Bernardo Dominic', image: 'bernardodominic.png' },
    { name: 'Elwin Sharvill', image: 'elwinsharvill.png' },
    { name: 'Ioni Bowcher', image: 'ionibowcher.png' },
    { name: 'Ivan Magalhaes', image: 'ivanmagalhaes.png' },
    { name: 'Onyama Limba', image: 'onyamalimba.png' },
    { name: 'Stephen Shaw', image: 'stephenshaw.png' },
    { name: 'XuXue Feng', image: 'xuxuefeng.png' }
]);
const statuses = ref([
    { label: 'Unqualified', value: 'unqualified' },
    { label: 'Qualified', value: 'qualified' },
    { label: 'New', value: 'new' },
    { label: 'Negotiation', value: 'negotiation' },
    { label: 'Renewal', value: 'renewal' },
    { label: 'Proposal', value: 'proposal' }
]);
const verifiedOptions = ref([
    { label: 'All', value: null },
    { label: 'Verified', value: true },
    { label: 'Unverified', value: false }
]);
const loading = ref(true);

onMounted(() => {
    CustomerService.getCustomersLarge().then((data) => {
        customers.value = getCustomers(data);
        loading.value = false;
    });
});

const initFilters = () => {
    filters.value = {
        global: { value: null, matchMode: FilterMatchMode.CONTAINS },
        name: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.STARTS_WITH }] },
        'country.name': { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.CONTAINS }] },
        'representative.name': { value: null, matchMode: FilterMatchMode.EQUALS },
        date: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.DATE_IS }] },
        balance: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.GREATER_THAN_OR_EQUAL_TO }] },
        status: { value: null, matchMode: FilterMatchMode.EQUALS },
        activity: { value: [0, 100], matchMode: FilterMatchMode.BETWEEN },
        verified: { value: null, matchMode: FilterMatchMode.EQUALS }
    };
};

initFilters();

const formatDate = (value) => {
    return value.toLocaleDateString('en-US', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
};
const formatCurrency = (value) => {
    return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
};
const clearFilter = () => {
    initFilters();
};
const getRepImage = (name) => {
    return representatives.value.find((r) => r.name === name)?.image;
};
const getCustomers = (data) => {
    return [...(data || [])].map((d) => {
        d.date = new Date(d.date);

        return d;
    });
};
const getSeverity = (status) => {
    switch (status) {
        case 'unqualified':
            return 'danger';

        case 'qualified':
            return 'success';

        case 'new':
            return 'info';

        case 'negotiation':
            return 'warn';

        case 'renewal':
            return 'secondary';

        case 'proposal':
            return 'info';
    }
};
<\/script>
```

## Export

Export table data to CSV with customizable fields and headers.

```vue
<template>
    <div>
        <div class="flex items-center justify-between gap-3 mb-3">
            <span class="text-sm text-surface-500 dark:text-surface-400">Export visible rows to CSV with custom column headers.</span>
            <Button type="button" size="small" @click="exportCSV($event)">
                <FileExport />
                Export CSV
            </Button>
        </div>
        <DataTable ref="dt" :value="products" exportFilename="products" tableStyle="min-width: 50rem">
            <Column field="code" header="Product" exportHeader="Product Code">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="36" height="36" class="rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column field="category" header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column field="quantity" header="Qty"></Column>
            <Column field="price" header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column field="inventoryStatus" header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';
import FileExport from '@primeicons/vue/file-export';

const dt = ref();
const products = ref();

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 8)));
});

const exportCSV = () => {
    dt.value.exportCSV();
};
const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';
        case 'LOWSTOCK':
            return 'warn';
        case 'OUTOFSTOCK':
            return 'danger';
        default:
            return 'secondary';
    }
};
const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';
        case 'LOWSTOCK':
            return 'Low Stock';
        case 'OUTOFSTOCK':
            return 'Out of Stock';
        default:
            return status;
    }
};
<\/script>
```

## Lazy

Lazy mode is handy to deal with large datasets, instead of loading the entire data, small chunks of data is loaded by invoking corresponding callbacks everytime paging , sorting and filtering occurs. Sample below imitates lazy loading data from a remote datasource using an in-memory list and timeouts to mimic network connection. Enabling the lazy property and assigning the logical number of rows to totalRecords by doing a projection query are the key elements of the implementation so that paginator displays the UI assuming there are actually records of totalRecords size although in reality they are not present on page, only the records that are displayed on the current page exist. Note that, the implementation of checkbox selection in lazy mode needs to be handled manually as in this example since the DataTable cannot know about the whole dataset.

```vue
P${String(i + 1).padStart(3, '0')}
```

## Overlay

Set the loading property to display a mask layer over the table while data is being fetched. The overlay content can be customized with the loading slot.

```vue
<template>
    <div>
        <div class="mb-3 flex items-center justify-between gap-3">
            <span class="text-sm text-surface-500 dark:text-surface-400">Click refresh to simulate a network fetch.</span>
            <Button size="small" :disabled="loading" @click="refresh">
                <Refresh />
                Refresh
            </Button>
        </div>
        <DataTable :value="products" :loading="loading" tableStyle="min-width: 50rem">
            <Column header="Product">
                <template #body="{ data }">
                    <div class="flex items-center gap-3">
                        <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="40" height="40" class="rounded-md shadow" />
                        <div class="flex flex-col">
                            <span class="font-medium">{{ data.name }}</span>
                            <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                        </div>
                    </div>
                </template>
            </Column>
            <Column header="Category">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column header="Price">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
            <template #loading>
                <div class="flex flex-col items-center gap-2">
                    <Spinner :size="40" class="animate-spin text-primary" />
                    <span class="text-sm text-surface-600 dark:text-surface-300">Loading products…</span>
                </div>
            </template>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { ProductService } from '@/service/ProductService';
import Refresh from '@primeicons/vue/refresh';
import Spinner from '@primeicons/vue/spinner';

const products = ref();
const loading = ref(false);

const refresh = () => {
    loading.value = true;

    setTimeout(() => {
        ProductService.getProductsSmall().then((data) => {
            products.value = data.slice(0, 6);
            loading.value = false;
        });
    }, 1500);
};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

onMounted(() => {
    refresh();
});
<\/script>
```

## Skeleton

Render placeholder rows filled with Skeleton elements while the request is in flight.

```vue
<template>
    <div>
        <div class="mb-3 flex items-center justify-between gap-3">
            <span class="text-sm text-surface-500 dark:text-surface-400">Click refresh to simulate a network fetch.</span>
            <Button type="button" size="small" :disabled="loading" @click="refresh">
                <Refresh />
                Refresh
            </Button>
        </div>
        <DataTable :value="rows" tableStyle="min-width: 50rem">
            <Column header="Product" style="width: 40%">
                <template #body="{ data }">
                    <template v-if="loading">
                        <div class="flex items-center gap-3">
                            <Skeleton width="40px" height="40px" borderRadius="6px" />
                            <div class="flex flex-col gap-1">
                                <Skeleton width="8rem" height="0.6rem" borderRadius="4px" />
                                <Skeleton width="5rem" height="0.55rem" borderRadius="4px" />
                            </div>
                        </div>
                    </template>
                    <template v-else>
                        <div class="flex items-center gap-3">
                            <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${data.image}\`" :alt="data.name" width="40" height="40" class="rounded-md shadow" />
                            <div class="flex flex-col">
                                <span class="font-medium">{{ data.name }}</span>
                                <span class="text-xs text-surface-500 dark:text-surface-400">{{ data.code }}</span>
                            </div>
                        </div>
                    </template>
                </template>
            </Column>
            <Column header="Category" style="width: 20%">
                <template #body="{ data }">
                    <Skeleton v-if="loading" width="5rem" height="1rem" borderRadius="16px" />
                    <Tag v-else :value="data.category" severity="secondary" />
                </template>
            </Column>
            <Column header="Price" style="width: 15%">
                <template #body="{ data }">
                    <Skeleton v-if="loading" width="3rem" height="0.6rem" borderRadius="4px" />
                    <span v-else class="font-semibold">{{ '$' + data.price }}</span>
                </template>
            </Column>
            <Column header="Status" style="width: 25%">
                <template #body="{ data }">
                    <Skeleton v-if="loading" width="6rem" height="1rem" borderRadius="16px" />
                    <Tag v-else :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { ProductService } from '@/service/ProductService';
import Refresh from '@primeicons/vue/refresh';

const products = ref([]);
const placeholders = Array.from({ length: 6 }, (_, i) => ({ id: i.toString() }));
const loading = ref(false);

const rows = computed(() => (loading.value ? placeholders : products.value));

const refresh = () => {
    loading.value = true;
    products.value = [];

    setTimeout(() => {
        ProductService.getProductsSmall().then((data) => {
            products.value = data.slice(0, 6);
            loading.value = false;
        });
    }, 1500);
};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};

onMounted(() => {
    refresh();
});
<\/script>
```

## Empty State

Custom empty state when no data is available, using the empty template.

```vue
<template>
    <div>
        <DataTable :value="[]" tableStyle="min-width: 50rem">
            <Column field="name" header="Product"></Column>
            <Column field="category" header="Category"></Column>
            <Column field="price" header="Price"></Column>
            <Column field="status" header="Status"></Column>
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-10 text-center">
                    <div class="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                        <Inbox class="w-7 h-7 text-surface-400 dark:text-surface-500" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">No products yet</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Add your first product to see it listed here.</p>
                    </div>
                    <Button size="small">
                        <Plus />
                        Add product
                    </Button>
                </div>
            </template>
        </DataTable>
    </div>
</template>

<script setup>
import Inbox from '@primeicons/vue/inbox';
import Plus from '@primeicons/vue/plus';
<\/script>
```

## Dynamic Columns

Columns can be defined dynamically using the v-for directive.

```vue
<template>
    <div>
        <DataTable :value="products" tableStyle="min-width: 50rem">
            <Column v-for="col of columns" :key="col.field" :field="col.field" :header="col.header"></Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsMini().then((data) => (products.value = data));
});

const products = ref();
const columns = [
    { field: 'code', header: 'Code' },
    { field: 'name', header: 'Name' },
    { field: 'category', header: 'Category' },
    { field: 'quantity', header: 'Quantity' }
];

<\/script>
```

## Template

Custom content at header , body and footer sections are supported via templating.

```vue
<template>
    <div>
        <DataTable :value="products" tableStyle="min-width: 60rem">
            <template #header>
                <div class="flex items-center justify-between">
                    <span class="text-lg font-bold">Products</span>
                    <Button iconOnly rounded raised>
                        <Refresh />
                    </Button>
                </div>
            </template>
            <Column field="name" header="Name"></Column>
            <Column header="Image">
                <template #body="slotProps">
                    <img :src="\`https://primefaces.org/cdn/primevue/images/product/\${slotProps.data.image}\`" :alt="slotProps.data.image" class="w-24 rounded" />
                </template>
            </Column>
            <Column field="price" header="Price">
                <template #body="slotProps">
                    {{ '$' + slotProps.data.price }}
                </template>
            </Column>
            <Column field="category" header="Category"></Column>
            <Column field="rating" header="Reviews">
                <template #body="slotProps">
                    <Rating :modelValue="slotProps.data.rating" readonly />
                </template>
            </Column>
            <Column header="Status">
                <template #body="slotProps">
                    <Tag :value="slotProps.data.inventoryStatus" :severity="getSeverity(slotProps.data)" />
                </template>
            </Column>
            <template #footer>
                <div class="text-sm">In total there are {{ products ? products.length : 0 }} products.</div>
            </template>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';
import Refresh from '@primeicons/vue/refresh';

onMounted(() => {
    ProductService.getProductsMini().then((data) => (products.value = data));
});

const products = ref();
const getSeverity = (product) => {
    switch (product.inventoryStatus) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return undefined;
    }
};

<\/script>
```

## Conditional Style

Particular rows and cells can be styled based on conditions. The rowClass receives a row data as a parameter to return a style class for a row whereas cells are customized using the body template.

```vue
<template>
    <div>
        <DataTable :value="products" :rowClass="rowClass" :rowStyle="rowStyle" tableStyle="min-width: 50rem">
            <Column field="code" header="Code"></Column>
            <Column field="name" header="Name"></Column>
            <Column field="category" header="Category"></Column>
            <Column field="quantity" header="Quantity">
                <template #body="slotProps">
                    <Badge :value="slotProps.data.quantity" :severity="stockSeverity(slotProps.data)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref();

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data));
});

const rowClass = (data) => {
    return [{ 'bg-primary! text-primary-contrast!': data.category === 'Fitness' }];
};
const rowStyle = (data) => {
    if (data.quantity === 0) {
        return { fontWeight: 'bold', fontStyle: 'italic' };
    }
};
const stockSeverity = (data) => {
    if (data.quantity === 0) return 'danger';
    else if (data.quantity > 0 && data.quantity < 10) return 'warn';
    else return 'success';
}

<\/script>
```

## Preload

Virtual Scrolling is an efficient way to render large amount data. Usage is similar to regular scrolling with the addition of virtualScrollerOptions property to define a fixed itemSize . Internally, VirtualScroller component is utilized so refer to the API of VirtualScroller for more information about the available options. In this example, 10000 preloaded records are rendered by the Table.

```vue
<template>
    <div>
        <DataTable :value="cars" scrollable scrollHeight="400px" :virtualScrollerOptions="{ itemSize: 46 }" tableStyle="min-width: 50rem">
            <Column v-for="col of columns" :key="col.field" :field="col.field" :header="col.header" style="width: 20%; height: 46px"></Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { CarService } from '@/service/CarService';

const cars = ref();
const columns = ref([
    { field: 'id', header: 'Id' },
    { field: 'vin', header: 'Vin' },
    { field: 'year', header: 'Year' },
    { field: 'brand', header: 'Brand' },
    { field: 'color', header: 'Color' }
]);

onMounted(() => {
    cars.value = Array.from({ length: 10000 }).map((_, i) => CarService.generateCar(i + 1));
});
<\/script>
```

## Lazy

VirtualScroller is a performance-approach to handle huge data efficiently. Setting lazy on virtualScrollerOptions and providing an itemSize in pixels would be enough to enable this functionality. It is also suggested to use the same itemSize value on the row height inside the body template. In sample below, an in-memory list and timeout is used to mimic fetching from a remote datasource. The virtualCars is an empty array that is populated on scroll.

```vue
<template>
    <div>
        <DataTable :value="virtualCars" scrollable scrollHeight="400px" tableStyle="min-width: 50rem"
                :virtualScrollerOptions="{ lazy: true, onLazyLoad: loadCarsLazy, itemSize: 46, delay: 200, showLoader: true, loading: lazyLoading, numToleratedItems: 10 }">
            <Column field="id" header="Id" style="width: 20%; height: 46px">
                <template #loading>
                    <div class="flex items-center" :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }">
                        <Skeleton width="40%" height="1rem" />
                    </div>
                </template>
            </Column>
            <Column field="vin" header="Vin" style="width: 20%; height: 46px">
                <template #loading>
                    <div class="flex items-center" :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }">
                        <Skeleton width="60%" height="1rem" />
                    </div>
                </template>
            </Column>
            <Column field="year" header="Year" style="width: 20%; height: 46px">
                <template #loading>
                    <div class="flex items-center" :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }">
                        <Skeleton width="30%" height="1rem" />
                    </div>
                </template>
            </Column>
            <Column field="brand" header="Brand" style="width: 20%; height: 46px">
                <template #loading>
                    <div class="flex items-center" :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }">
                        <Skeleton width="60%" height="1rem" />
                    </div>
                </template>
            </Column>
            <Column field="color" header="Color" style="width: 20%; height: 46px">
                <template #loading>
                    <div class="flex items-center" :style="{ height: '17px', 'flex-grow': '1', overflow: 'hidden' }">
                        <Skeleton width="40%" height="1rem" />
                    </div>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { CarService } from '@/service/CarService';

const cars = ref();
const virtualCars = ref(Array.from({ length: 10000 }));
const lazyLoading = ref(false);
const loadLazyTimeout = ref();

const loadCarsLazy = (event) => {
    !lazyLoading.value && (lazyLoading.value = true);

    if (loadLazyTimeout.value) {
        clearTimeout(loadLazyTimeout.value);
    }

    //simulate remote connection with a timeout
    loadLazyTimeout.value = setTimeout(() => {
        let _virtualCars = [...virtualCars.value];
        let { first, last } = event;

        //load data of required page
        const loadedCars = cars.value.slice(first, last);

        //populate page of virtual cars
        Array.prototype.splice.apply(_virtualCars, [...[first, last - first], ...loadedCars]);

        virtualCars.value = _virtualCars;
        lazyLoading.value = false;
    }, Math.random() * 1000 + 250);
};

onMounted(() => {
    cars.value = Array.from({ length: 10000 }).map((_, i) => CarService.generateCar(i + 1));
});
<\/script>
```

## Context Menu

DataTable has exclusive integration with ContextMenu using the contextMenu property to attach a menu, the row-contextmenu event to display the menu whenever a row is right clicked and the contextMenuSelection property to get a hold of the right clicked row.

```vue
<template>
    <div>
        <ContextMenu ref="cm" :model="menuModel" @hide="selectedProduct = null" />
        <DataTable :value="products" contextMenu v-model:contextMenuSelection="selectedProduct" dataKey="code"
                @row-contextmenu="onRowContextMenu" tableStyle="min-width: 50rem">
            <Column field="code" header="Code"></Column>
            <Column field="name" header="Name"></Column>
            <Column field="category" header="Category"></Column>
            <Column field="price" header="Price">
                <template #body="{ data }">
                    {{ '$' + data.price }}
                </template>
            </Column>
        </DataTable>
        <Toast />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import Search from '@primeicons/vue/search';
import Times from '@primeicons/vue/times';
import { ProductService } from '@/service/ProductService';

onMounted(() => {
    ProductService.getProductsMini().then((data) => (products.value = data));
});

const cm = ref();
const toast = useToast();
const products = ref();
const selectedProduct = ref();
const menuModel = ref([
    {label: 'View', icon: Search, command: () => viewProduct(selectedProduct)},
    {label: 'Delete', icon: Times, command: () => deleteProduct(selectedProduct)}
]);
const onRowContextMenu = (event) => {
    cm.value.show(event.originalEvent);
};
const viewProduct = (product) => {
    toast.add({severity: 'info', summary: 'Product Selected', detail: product.value.name, life: 3000});
};
const deleteProduct = (product) => {
    products.value = products.value.filter((p) => p.id !== product.value.id);
    toast.add({severity: 'error', summary: 'Product Deleted', detail: product.value.name, life: 3000});
    selectedProduct.value = null;
};

<\/script>
```

## Stateful

Stateful table allows keeping the state such as page, sort and filtering either at local storage or session storage so that when the page is visited again, table would render the data using the last settings. Change the state of the table e.g paginate, navigate away and then return to this table again to test this feature, the setting is set as session with the stateStorage property so that Table retains the state until the browser is closed. Other alternative is local referring to localStorage for an extended lifetime.

```vue
<template>
    <div>
        <DataTable v-model:filters="filters" v-model:selection="selectedCustomer" :value="customers" stateStorage="session"
            stateKey="dt-state-demo-session" paginator :rows="5" selectionMode="single" dataKey="id"
            :globalFilterFields="['name', 'country.name', 'representative.name', 'status']" tableStyle="min-width: 50rem">
            <template #header>
                <IconField>
                    <InputIcon>
                        <Search />
                    </InputIcon>
                    <InputText v-model="filters['global'].value" placeholder="Global Search" />
                </IconField>
            </template>
            <Column field="name" header="Name" sortable style="width: 25%"></Column>
            <Column field="country.name" header="Country" sortable style="width: 25%">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img alt="flag" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${data.country.code}\`" style="width: 24px" />
                        <span>{{ data.country.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="representative.name" header="Representative" sortable style="width: 25%">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <img :alt="data.representative.name" :src="\`https://primefaces.org/cdn/primevue/images/avatar/\${data.representative.image}\`" style="width: 32px" />
                        <span>{{ data.representative.name }}</span>
                    </div>
                </template>
            </Column>
            <Column field="status" header="Status" sortable style="width: 25%">
                <template #body="{ data }">
                    <Tag :value="data.status" :severity="getSeverity(data.status)" />
                </template>
            </Column>
            <template #empty> No customers found. </template>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CustomerService } from '@/service/CustomerService';
import { FilterMatchMode } from '@primevue/core/api';
import Search from '@primeicons/vue/search';

const customers = ref();
const selectedCustomer = ref();
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS }
});

onMounted(() => {
    CustomerService.getCustomersSmall().then((data) => (customers.value = data));
});

const getSeverity = (status) => {
    switch (status) {
        case 'unqualified':
            return 'danger';

        case 'qualified':
            return 'success';

        case 'new':
            return 'info';

        case 'negotiation':
            return 'warn';

        case 'renewal':
            return null;
    }
};
<\/script>
```

## Advanced

Sorting, per-column and global filtering, and cell editing composed in a single table.

```vue
<template>
    <div>
        <div class="mb-3 flex justify-end">
            <IconField>
                <InputIcon>
                    <Search />
                </InputIcon>
                <InputText v-model="filters['global'].value" size="small" placeholder="Keyword search" />
            </IconField>
        </div>
        <DataTable v-model:filters="filters" :value="products" dataKey="id" removableSort filterDisplay="row" :globalFilterFields="['name', 'category', 'code']"
            editMode="cell" @cell-edit-complete="onCellEditComplete"
            :pt="{
                table: { style: 'min-width: 60rem' },
                column: {
                    bodycell: ({ state }) => ({
                        class: [{ 'py-0!': state['d_editing'] }]
                    })
                }
            }"
        >
            <template #empty>
                <div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
                    <div class="w-14 h-14 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                        <Database :size="20" class="text-surface-400 dark:text-surface-500" />
                    </div>
                    <div>
                        <p class="m-0 font-semibold text-surface-900 dark:text-surface-0">No products found</p>
                        <p class="mt-1 text-sm text-surface-500 dark:text-surface-400">Try adjusting your search or filters.</p>
                    </div>
                </div>
            </template>
            <Column field="name" header="Name" sortable :showFilterMenu="false" style="min-width: 14rem">
                <template #body="{ data }">
                    <span class="font-medium">{{ data.name }}</span>
                </template>
                <template #filter="{ filterModel, filterCallback }">
                    <InputText v-model="filterModel.value" size="small" type="text" @input="filterCallback()" placeholder="Search" fluid />
                </template>
                <template #editor="{ data }">
                    <InputText v-model="data.name" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="category" header="Category" sortable :showFilterMenu="false" style="min-width: 12rem">
                <template #body="{ data }">
                    <Tag :value="data.category" severity="secondary" />
                </template>
                <template #filter="{ filterModel, filterCallback }">
                    <InputText v-model="filterModel.value" size="small" type="text" @input="filterCallback()" placeholder="Search" fluid />
                </template>
                <template #editor="{ data }">
                    <InputText v-model="data.category" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="price" header="Price" sortable style="min-width: 10rem">
                <template #body="{ data }">
                    <span class="font-semibold">{{ '$' + data.price }}</span>
                </template>
                <template #editor="{ data }">
                    <InputNumber v-model="data.price" mode="currency" currency="USD" locale="en-US" autofocus fluid size="small" />
                </template>
            </Column>
            <Column field="quantity" header="Qty" sortable style="min-width: 8rem"></Column>
            <Column field="inventoryStatus" header="Status" sortable style="min-width: 10rem">
                <template #body="{ data }">
                    <Tag :value="getSeverityLabel(data.inventoryStatus)" :severity="getSeverity(data.inventoryStatus)" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { FilterMatchMode } from '@primevue/core/api';
import Database from '@primeicons/vue/database';
import Search from '@primeicons/vue/search';
import { ProductService } from '@/service/ProductService';

const products = ref();
const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    name: { value: null, matchMode: FilterMatchMode.CONTAINS },
    category: { value: null, matchMode: FilterMatchMode.CONTAINS }
});

onMounted(() => {
    ProductService.getProductsSmall().then((data) => (products.value = data.slice(0, 10)));
});

const onCellEditComplete = (event) => {
    let { data, newValue, field } = event;

    if (field === 'price') {
        if (newValue != null) data[field] = newValue;
        else event.preventDefault();
    } else {
        if (newValue && newValue.trim().length > 0) data[field] = newValue;
        else event.preventDefault();
    }
};

const getSeverity = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'success';

        case 'LOWSTOCK':
            return 'warn';

        case 'OUTOFSTOCK':
            return 'danger';

        default:
            return 'secondary';
    }
};

const getSeverityLabel = (status) => {
    switch (status) {
        case 'INSTOCK':
            return 'In Stock';

        case 'LOWSTOCK':
            return 'Low Stock';

        case 'OUTOFSTOCK':
            return 'Out of Stock';

        default:
            return status;
    }
};
<\/script>
```

## Database Editor

A spreadsheet-style table editor composed from DataTable , Menu , Checkbox , Drawer and Select : typed column headers with a per-column menu (sort, copy, edit, freeze, delete), select-all and per-row checkboxes, a global filter, in-place cell editing, frozen columns, an empty-table state, plus working insert-row and add/edit-column flows that open a side drawer.

```vue
<template>
    <div ref="dbContainer" class="relative w-full overflow-hidden rounded-lg border border-surface-200 dark:border-surface-700">
        <div class="flex items-center gap-2 border-b border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-900 px-3 py-2">
            <IconField class="flex-1 max-w-md">
                <InputIcon>
                    <Search />
                </InputIcon>
                <InputText v-model="filters['global'].value" type="text" placeholder="Filter by id, created_at or email" size="small" fluid />
            </IconField>
            <div class="flex-1"></div>
            <Button v-if="selectedRows.length" size="small" severity="danger" variant="outlined" @click="deleteSelected">
                <Trash class="mr-1" />
                Delete {{ selectedRows.length }}
            </Button>
            <Button size="small" @click="rowDrawer = true">
                <Plus class="mr-1" />
                Insert
            </Button>
        </div>

        <DataTable v-model:selection="selectedRows" v-model:filters="filters" :value="sortedRows" dataKey="__rid" :globalFilterFields="globalFilterFields"
            scrollable editMode="cell" @cell-edit-complete="onCellEditComplete" paginator :rows="10" :rowsPerPageOptions="[10, 20, 50, 100]"
            reorderableColumns @column-reorder="onColReorder"
            currentPageReportTemplate="Page {currentPage} of {totalPages} • {totalRecords} records"
            paginatorTemplate="PrevPageLink CurrentPageReport RowsPerPageDropdown NextPageLink"
            :pt="{ column: { headerCell: { onDragStart: () => colMenu.hide() }, bodycell: ({ state }) => ({ class: [{ 'py-0!': state['d_editing'] }] }) } }"
        >
            <template #empty>
                <div class="py-24 text-center text-sm text-surface-500 dark:text-surface-400">This table is empty</div>
            </template>
            <Column columnKey="__selection__" selectionMode="multiple" frozen :reorderableColumn="false" style="width: 3rem" />
            <Column v-for="col of columns" :key="col.field" :field="col.field" :frozen="col.frozen" style="min-width: 12rem">
                <template #header>
                    <div class="flex items-center justify-between gap-2 w-full">
                        <span class="inline-flex items-center gap-1.5 whitespace-nowrap text-xs">
                            <Key v-if="col.pk" class="text-emerald-500" style="width: 13px" />
                            <Lock v-if="col.frozen" class="text-surface-400" style="width: 11px" />
                            <span class="font-semibold">{{ col.field }}</span>
                            <span class="font-mono font-normal text-surface-400 dark:text-surface-500">{{ col.type }}</span>
                            <ArrowUp v-if="sortField === col.field && sortOrder === 1" style="width: 11px" />
                            <ArrowDown v-if="sortField === col.field && sortOrder === -1" style="width: 11px" />
                        </span>
                        <Button iconOnly variant="text" severity="secondary" size="small" :aria-label="\`\${col.field} options\`" @click="toggleColMenu($event, col)">
                            <template #icon>
                                <ChevronDown />
                            </template>
                        </Button>
                    </div>
                </template>
                <template #body="{ data }">
                    <span class="flex h-7 items-center whitespace-nowrap text-xs" :class="{ 'font-mono': col.type !== 'text' || col.field === 'plan' }">
                        <template v-if="data[col.field] != null">{{ data[col.field] }}</template>
                        <span v-else class="text-surface-400 dark:text-surface-600">NULL</span>
                    </span>
                </template>
                <template #editor="{ data }">
                    <Select v-if="col.field === 'plan'" v-model="data[col.field]" :options="planOptions" optionLabel="label" optionValue="value" size="small" fluid />
                    <InputText v-else v-model="data[col.field]" autofocus size="small" fluid />
                </template>
            </Column>
            <Column columnKey="__add_column__" :reorderableColumn="false" style="width: 3rem">
                <template #header>
                    <Button iconOnly variant="text" severity="secondary" size="small" aria-label="Add column" @click="openAddColumn">
                        <template #icon>
                            <Plus />
                        </template>
                    </Button>
                </template>
            </Column>
        </DataTable>

        <Menu ref="colMenu" :model="colMenuModel" popup />

        <Drawer v-model:visible="rowDrawer" position="right" header="Insert row" :appendTo="dbContainerEl" class="w-full! md:w-96!">
            <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-2">
                    <label for="draft-email" class="font-medium">email <span class="font-mono text-xs text-surface-400">text</span></label>
                    <InputText id="draft-email" v-model="draftEmail" placeholder="name@example.com" fluid />
                </div>
                <div class="flex flex-col gap-2">
                    <label class="font-medium">plan <span class="font-mono text-xs text-surface-400">text</span></label>
                    <Select v-model="draftPlan" :options="planOptions" optionLabel="label" optionValue="value" size="small" fluid />
                </div>
                <p class="text-xs text-surface-500 dark:text-surface-400"><span class="font-mono">id</span> and <span class="font-mono">created_at</span> are filled automatically.</p>
                <div class="flex justify-end gap-2 pt-2">
                    <Button variant="text" severity="secondary" @click="rowDrawer = false">Cancel</Button>
                    <Button :disabled="!draftEmail.trim()" @click="insertRow">Save</Button>
                </div>
            </div>
        </Drawer>

        <Drawer v-model:visible="colDrawer" position="right" :header="editingField ? 'Edit column' : 'Add column'" :appendTo="dbContainerEl" class="w-full! md:w-96!">
            <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-2">
                    <label for="draft-col" class="font-medium">Name</label>
                    <InputText id="draft-col" v-model="draftColName" placeholder="column_name" fluid />
                </div>
                <div class="flex flex-col gap-2">
                    <label class="font-medium">Type</label>
                    <Select v-model="draftColType" :options="typeOptions" optionLabel="label" optionValue="value" size="small" fluid />
                </div>
                <div class="flex justify-end gap-2 pt-2">
                    <Button variant="text" severity="secondary" @click="colDrawer = false">Cancel</Button>
                    <Button :disabled="!draftColName.trim() || columns.some((c) => c.field === draftColName.trim() && c.field !== editingField)" @click="saveColumn">{{ editingField ? 'Save' : 'Add' }}</Button>
                </div>
            </div>
        </Drawer>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, useTemplateRef } from 'vue';
import { FilterMatchMode } from '@primevue/core/api';
import ArrowDown from '@primeicons/vue/arrow-down';
import ArrowUp from '@primeicons/vue/arrow-up';
import ChevronDown from '@primeicons/vue/chevron-down';
import Copy from '@primeicons/vue/copy';
import Key from '@primeicons/vue/key';
import Lock from '@primeicons/vue/lock';
import Pencil from '@primeicons/vue/pencil';
import Plus from '@primeicons/vue/plus';
import Search from '@primeicons/vue/search';
import Trash from '@primeicons/vue/trash';

const names = ['amy', 'bernardo', 'asiya', 'ioni', 'stephen', 'xuxue', 'onyama', 'ivan', 'anna', 'elwin', 'kadir', 'mira', 'leon', 'priya', 'tomas', 'nadia', 'oscar', 'hana', 'felix', 'sara'];
const plans = ['free', 'pro', 'team'];
const seed = names.map((name, i) => {
    const day = String((i % 27) + 1).padStart(2, '0');
    const month = String((i % 12) + 1).padStart(2, '0');
    return { __rid: i + 1, id: i + 1, created_at: \`2026-\${month}-\${day} 09:1\${i % 6}:4\${i % 9}+00\`, email: \`\${name}@acme.dev\`, plan: plans[i % plans.length] };
});

const dbContainer = useTemplateRef('dbContainer');
const colMenu = useTemplateRef('colMenu');
const dbContainerEl = ref(null);
const rows = ref(seed);
const columns = ref([
    { field: 'id', type: 'int8', pk: true },
    { field: 'created_at', type: 'timestamptz' },
    { field: 'email', type: 'text' },
    { field: 'plan', type: 'text' }
]);
const selectedRows = ref([]);
const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });
const sortField = ref(null);
const sortOrder = ref(0);
const colMenuModel = ref([]);
const rowDrawer = ref(false);
const draftEmail = ref('');
const draftPlan = ref('free');
const colDrawer = ref(false);
const editingField = ref(null);
const draftColName = ref('');
const draftColType = ref('text');
const planOptions = [
    { label: 'free', value: 'free' },
    { label: 'pro', value: 'pro' },
    { label: 'team', value: 'team' }
];
const typeOptions = [
    { label: 'text', value: 'text' },
    { label: 'int8', value: 'int8' },
    { label: 'bool', value: 'bool' },
    { label: 'timestamptz', value: 'timestamptz' }
];

const globalFilterFields = computed(() => columns.value.map((c) => c.field));
const sortedRows = computed(() => {
    if (!sortField.value || !sortOrder.value) return rows.value;
    const f = sortField.value;
    const o = sortOrder.value;
    return [...rows.value].sort((a, b) => {
        const av = a[f];
        const bv = b[f];
        if (av == null) return 1;
        if (bv == null) return -1;
        const r = av < bv ? -1 : av > bv ? 1 : 0;
        return o * r;
    });
});

onMounted(() => (dbContainerEl.value = dbContainer.value));

const sortBy = (field, order) => {
    sortField.value = field;
    sortOrder.value = order;
};
const copyName = (field) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) navigator.clipboard.writeText(field);
};
const freezeColumn = (field) => (columns.value = columns.value.map((c) => (c.field === field ? { ...c, frozen: !c.frozen } : c)));
const deleteColumn = (field) => (columns.value = columns.value.filter((c) => c.field !== field));
const openAddColumn = () => {
    editingField.value = null;
    draftColName.value = '';
    draftColType.value = 'text';
    colDrawer.value = true;
};
const openEditColumn = (col) => {
    editingField.value = col.field;
    draftColName.value = col.field;
    draftColType.value = col.type;
    colDrawer.value = true;
};
const saveColumn = () => {
    const name = draftColName.value.trim();
    if (!name) return;
    if (editingField.value) {
        const oldField = editingField.value;
        columns.value = columns.value.map((c) => (c.field === oldField ? { ...c, field: name, type: draftColType.value } : c));
        if (name !== oldField) {
            rows.value = rows.value.map((r) => {
                const { [oldField]: oldValue, ...rest } = r;
                return { ...rest, [name]: oldValue };
            });
        }
    } else {
        if (columns.value.some((c) => c.field === name)) return;
        columns.value = [...columns.value, { field: name, type: draftColType.value }];
    }
    colDrawer.value = false;
    editingField.value = null;
};
const insertRow = () => {
    if (!draftEmail.value.trim()) return;
    const nextRid = rows.value.reduce((max, r) => Math.max(max, r.__rid), 0) + 1;
    const nextId = rows.value.reduce((max, r) => Math.max(max, Number(r.id) || 0), 0) + 1;
    rows.value = [...rows.value, { __rid: nextRid, id: nextId, created_at: '2026-06-04 12:00:00+00', email: draftEmail.value.trim(), plan: draftPlan.value }];
    draftEmail.value = '';
    draftPlan.value = 'free';
    rowDrawer.value = false;
};
const deleteSelected = () => {
    const selectedIds = new Set(selectedRows.value.map((r) => r.__rid));
    rows.value = rows.value.filter((r) => !selectedIds.has(r.__rid));
    selectedRows.value = [];
};
const onColReorder = (event) => {
    const from = event.dragIndex - 1;
    const to = event.dropIndex - 1;
    if (from < 0 || from >= columns.value.length || to < 0 || to >= columns.value.length) return;
    const next = [...columns.value];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    columns.value = next;
};
const toggleColMenu = (event, col) => {
    colMenuModel.value = [
        { label: 'Sort Ascending', icon: ArrowUp, command: () => sortBy(col.field, 1) },
        { label: 'Sort Descending', icon: ArrowDown, command: () => sortBy(col.field, -1) },
        { separator: true },
        { label: 'Copy name', icon: Copy, command: () => copyName(col.field) },
        { label: 'Edit column', icon: Pencil, command: () => openEditColumn(col) },
        { label: col.frozen ? 'Unfreeze column' : 'Freeze column', icon: Lock, command: () => freezeColumn(col.field) },
        { separator: true },
        { label: 'Delete column', icon: Trash, class: 'text-red-600', command: () => deleteColumn(col.field) }
    ];
    colMenu.value.toggle(event);
};
const onCellEditComplete = (event) => {
    let { data, newValue, field } = event;
    if (newValue != null && String(newValue).trim().length > 0) data[field] = newValue;
    else event.preventDefault();
};
<\/script>
```

## Accessibility

Screen Reader DataTable uses a table element whose attributes can be extended with the tableProps option. This property allows passing aria roles and attributes like aria-label and aria-describedby to define the table for readers. Default role of the table is table . Header, body and footer elements use rowgroup , rows use row role, header cells have columnheader and body cells use cell roles. Sortable headers utilizer aria-sort attribute either set to "ascending" or "descending". Built-in checkbox and radiobutton components for row selection use checkbox and radiobutton . The label to describe them is retrieved from the aria.selectRow and aria.unselectRow properties of the locale API. Similarly header checkbox uses selectAll and unselectAll keys. When a row is selected, aria-selected is set to true on a row. The element to expand or collapse a row is a button with aria-expanded and aria-controls properties. Value to describe the buttons is derived from aria.expandRow and aria.collapseRow properties of the locale API. The filter menu button use aria.showFilterMenu and aria.hideFilterMenu properties as aria-label in addition to the aria-haspopup , aria-expanded and aria-controls to define the relation between the button and the overlay. Popup menu has dialog role with aria-modal as focus is kept within the overlay. The operator dropdown use aria.filterOperator and filter constraints dropdown use aria.filterConstraint properties. Buttons to add rules on the other hand utilize aria.addRule and aria.removeRule properties. The footer buttons similarly use aria.clear and aria.apply properties. filterInputProps of the Column component can be used to define aria labels for the built-in filter components, if a custom component is used with templating you also may define your own aria labels as well. Editable cells use custom templating so you need to manage aria roles and attributes manually if required. The row editor controls are button elements with aria.editRow , aria.cancelEdit and aria.saveEdit used for the aria-label . Paginator is a standalone component used inside the DataTable, refer to the paginator for more information about the accessibility features. Keyboard Support Any button element inside the DataTable used for cases like filter, row expansion, edit are tabbable and can be used with space and enter keys. Sortable Headers Keyboard Support Key Function tab Moves through the headers. enter Sorts the column. space Sorts the column. Filter Menu Keyboard Support Key Function tab Moves through the elements inside the popup. escape Hides the popup. enter Opens the popup. Selection Keyboard Support Key Function tab Moves focus to the first selected row, if there is none then first row receives the focus. up arrow Moves focus to the previous row. down arrow Moves focus to the next row. enter Toggles the selected state of the focused row depending on the metaKeySelection setting. space Toggles the selected state of the focused row depending on the metaKeySelection setting. home Moves focus to the first row. end Moves focus to the last row. shift + down arrow Moves focus to the next row and toggles the selection state. shift + up arrow Moves focus to the previous row and toggles the selection state. shift + space Selects the rows between the most recently selected row and the focused row. control + shift + home Selects the focused rows and all the options up to the first one. control + shift + end Selects the focused rows and all the options down to the last one. control + a Selects all rows.

## Data Table API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | null \| readonly T[] | - | An array of objects to display. |
| dataKey | keyof T \| Function | - | Name of the field that uniquely identifies the a record in the data. |
| rows | number | 0 | Number of rows to display per page. |
| first | number | 0 | Index of the first row to be displayed. |
| totalRecords | number | 0 | Number of total records, defaults to length of value when not defined. |
| paginator | boolean | false | When specified as true, enables the pagination. |
| paginatorPosition | any | bottom | Position of the paginator, options are 'top','bottom' or 'both'. |
| alwaysShowPaginator | boolean | true | Whether to show it even there is only one page. |
| paginatorTemplate | any | FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown | Template of the paginator. It can be customized using the template property using the predefined keys.  - FirstPageLink - PrevPageLink - PageLinks - NextPageLink - LastPageLink - RowsPerPageDropdown - JumpToPageDropdown - JumpToPageInput - CurrentPageReport |
| pageLinkSize | number | 5 | Number of page links to display. |
| rowsPerPageOptions | number[] | - | Array of integer values to display inside rows per page dropdown. |
| currentPageReportTemplate | string | '({currentPage} of {totalPages})' | Template of the current page report element. It displays information about the pagination state. Available placeholders are the following;  - {currentPage} - {totalPages} - {rows} - {first} - {last} - {totalRecords} |
| lazy | boolean | false | Defines if data is loaded and interacted with in lazy manner. |
| loading | boolean | false | Displays a loader to indicate data load is in progress. |
| loadingIcon | string | - | The icon to show while indicating data load is in progress. |
| sortField | keyof T \| Function | - | Property name or a getter function of a row data used for sorting by default |
| sortOrder | number | - | Order to sort the data by default. |
| nullSortOrder | number | 1 | Determines how null values are sorted. |
| defaultSortOrder | number | 1 | Default sort order of an unsorted column. |
| multiSortMeta | DataTableSortMeta[] | - | An array of SortMeta objects to sort the data. |
| sortMode | any | single | Defines whether sorting works on single column or on multiple columns. |
| removableSort | boolean | false | When enabled, columns can have an un-sorted state. |
| filters | DataTableFilterMeta | - | Filters object with key-value pairs to define the filters. |
| filterDisplay | any | - | Layout of the filter elements. |
| globalFilterFields | (keyof T \| Function)[] | - | An array of fields as string or function to use in global filtering. |
| filterLocale | string | - | Locale to use in filtering. The default locale is the host environment's current locale. |
| selection | any | - | Selected row in single mode or an array of values in multiple mode. |
| selectionMode | any | - | Specifies the selection mode. |
| compareSelectionBy | any | deepEquals | Algorithm to define if a row is selected. |
| metaKeySelection | boolean | false | Defines whether metaKey is requred or not for the selection. When true metaKey needs to be pressed to select or unselect an item and when set to false selection of each item can be toggled individually. On touch enabled devices, metaKeySelection is turned off automatically. |
| contextMenu | boolean | false | Enables context menu integration. |
| contextMenuSelection | any | - | Selected row instance with the ContextMenu. |
| selectAll | any | - | Whether all data is selected. |
| rowHover | boolean | false | When enabled, background of the rows change on hover. |
| csvSeparator | string | , | Character to use as the csv separator. |
| exportFilename | string | download | Name of the exported file. |
| exportFunction | Function | - |  |
| resizableColumns | boolean | false | When enabled, columns can be resized using drag and drop. |
| columnResizeMode | any | fit | Defines whether the overall table width. |
| reorderableColumns | boolean | false | When enabled, columns can be reordered using drag and drop. |
| expandedRows | null \| DataTableExpandedRows \| NoInfer<T>[] | - | A collection of row data display as expanded. |
| expandedRowIcon | string | - | Icon of the row toggler to display the row as expanded. |
| collapsedRowIcon | string | - | Icon of the row toggler to display the row as collapsed. |
| rowGroupMode | any | - | Defines the row group mode. |
| groupRowsBy | keyof T \| Function \| (keyof T)[] | - | One or more field names to use in row grouping. |
| expandableRowGroups | boolean | false | Whether the row groups can be expandable. |
| expandedRowGroups | DataTableExpandedRows \| NoInfer<T>[] | - | An array of group field values whose groups would be rendered as expanded. |
| stateStorage | any | session | Defines where a stateful table keeps its state. |
| stateKey | string | - | Unique identifier of a stateful table to use in state storage. |
| editMode | any | - | Defines the incell editing mode. |
| editingRows | DataTableEditingRows \| NoInfer<T>[] | - | A collection of rows to represent the current editing data in row edit mode. |
| rowClass | Function | - |  |
| rowStyle | Function | - |  |
| scrollable | boolean | false | When specified, enables horizontal and/or vertical scrolling. |
| scrollHeight | any | - | Height of the scroll viewport in fixed pixels or the 'flex' keyword for a dynamic size. |
| virtualScrollerOptions | any | - | Whether to use the virtualScroller feature. The properties of VirtualScroller component can be used like an object in it. Note: Currently only vertical orientation mode is supported. |
| frozenValue | null \| NoInfer<T>[] | - | Items of the frozen part in scrollable DataTable. |
| breakpoint | string | 960px | The breakpoint to define the maximum width boundary when using stack responsive layout. |
| showHeaders | boolean | true | Whether to display table headers |
| showGridlines | boolean | false | Whether to show grid lines between cells. |
| stripedRows | boolean | false | Whether to displays rows with alternating colors. |
| highlightOnSelect | boolean | false | Highlights automatically the first item. |
| size | any | - | Defines the size of the table. |
| tableStyle | string \| object | - | Inline style of the table element. |
| tableClass | string \| object | - | Style class of the table element. |
| tableProps | TableHTMLAttributes | - | Used to pass all properties of the TableHTMLAttributes to table element inside the component. |
| filterInputProps | InputHTMLAttributes | - | Used to pass all properties of the HTMLInputElement to the focusable filter input element inside the component. |
| filterButtonProps | Partial<DataTableFilterButtonPropsOptions> | - | Used to pass all filter button property object |
| editButtonProps | DataTableEditButtonPropsOptions | - | Used to pass all edit button property object |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DataTablePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| mask | DataTablePassThroughOptionType | Used to pass attributes to the mask's DOM element. |
| loadingIcon | DataTablePassThroughOptionType | Used to pass attributes to the loading icon's DOM element. |
| header | DataTablePassThroughOptionType | Used to pass attributes to the header's DOM element. |
| pcPaginator | any | Used to pass attributes to the Paginator component. |
| tableContainer | DataTablePassThroughOptionType | Used to pass attributes to the table container's DOM element. |
| virtualScroller | any | Used to pass attributes to the VirtualScroller component. |
| table | DataTablePassThroughOptionType | Used to pass attributes to the table's DOM element. |
| virtualScrollerSpacer | DataTablePassThroughOptionType | Used to pass attributes to the virtual scroller spacer's DOM element. |
| footer | DataTablePassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| thead | DataTablePassThroughOptionType | Used to pass attributes to the thead's DOM element. |
| headerRow | DataTablePassThroughOptionType | Used to pass attributes to the header row's DOM element. |
| tbody | DataTablePassThroughOptionType | Used to pass attributes to the tbody's DOM element. |
| rowGroupHeader | DataTablePassThroughOptionType | Used to pass attributes to the rowg roup header's DOM element. |
| rowGroupHeaderCell | DataTablePassThroughOptionType | Used to pass attributes to the row group header cell's DOM element. |
| bodyRow | DataTablePassThroughOptionType | Used to pass attributes to the body row's DOM element. |
| rowExpansion | DataTablePassThroughOptionType | Used to pass attributes to the row expansion's DOM element. |
| rowExpansionCell | DataTablePassThroughOptionType | Used to pass attributes to the row expansion cell's DOM element. |
| rowGroupFooter | DataTablePassThroughOptionType | Used to pass attributes to the row group footer's DOM element. |
| rowGroupFooterCell | DataTablePassThroughOptionType | Used to pass attributes to the row group footer cell's DOM element. |
| emptyMessage | DataTablePassThroughOptionType | Used to pass attributes to the empty message's DOM element. |
| emptyMessageCell | DataTablePassThroughOptionType | Used to pass attributes to the empty message cell's DOM element. |
| tfoot | DataTablePassThroughOptionType | Used to pass attributes to the tfoot's DOM element. |
| footerRow | DataTablePassThroughOptionType | Used to pass attributes to the footer row's DOM element. |
| columnResizeIndicator | DataTablePassThroughOptionType | Used to pass attributes to the column resize indicator's DOM element. |
| rowReorderIndicatorUp | DataTablePassThroughOptionType | Used to pass attributes to the row reorder indicator up's DOM element. |
| rowReorderIndicatorDown | DataTablePassThroughOptionType | Used to pass attributes to the row reorder indicator down's DOM element. |
| columnGroup | any | Used to pass attributes to the ColumnGroup helper components. |
| row | any | Used to pass attributes to the Row helper components. |
| column | any | Used to pass attributes to the Column helper components. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | DataTablePassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-datatable | Class name of the root element |
| p-datatable-mask | Class name of the mask element |
| p-datatable-loading-icon | Class name of the loading icon element |
| p-datatable-header | Class name of the header element |
| p-datatable-paginator-[position] | Class name of the paginator element |
| p-datatable-table-container | Class name of the table container element |
| p-datatable-table | Class name of the table element |
| p-datatable-thead | Class name of the thead element |
| p-datatable-column-resizer | Class name of the column resizer element |
| p-datatable-column-header-content | Class name of the column header content element |
| p-datatable-column-title | Class name of the column title element |
| p-datatable-sort-icon | Class name of the sort icon element |
| p-datatable-sort-badge | Class name of the sort badge element |
| p-datatable-filter | Class name of the filter element |
| p-datatable-filter-element-container | Class name of the filter element container element |
| p-datatable-column-filter-button | Class name of the column filter button element |
| p-datatable-column-filter-clear-button | Class name of the column filter clear button element |
| p-datatable-filter-overlay | Class name of the filter overlay element |
| p-datatable-filter-constraint-list | Class name of the filter constraint list element |
| p-datatable-filter-constraint | Class name of the filter constraint element |
| p-datatable-filter-constraint-separator | Class name of the filter constraint separator element |
| p-datatable-filter-operator | Class name of the filter operator element |
| p-datatable-filter-operator-dropdown | Class name of the filter operator dropdown element |
| p-datatable-filter-rule-list | Class name of the filter rule list element |
| p-datatable-filter-rule | Class name of the filter rule element |
| p-datatable-filter-constraint-dropdown | Class name of the filter constraint dropdown element |
| p-datatable-filter-remove-rule-button | Class name of the filter remove rule button element |
| p-datatable-filter-add-rule-button | Class name of the filter add rule button element |
| p-datatable-filter-buttonbar | Class name of the filter buttonbar element |
| p-datatable-filter-clear-button | Class name of the filter clear button element |
| p-datatable-filter-apply-button | Class name of the filter apply button element |
| p-datatable-tbody | Class name of the tbody element |
| p-datatable-row-group-header | Class name of the row group header element |
| p-datatable-row-toggle-button | Class name of the row toggle button element |
| p-datatable-row-toggle-icon | Class name of the row toggle icon element |
| p-datatable-row-expansion | Class name of the row expansion element |
| p-datatable-row-group-footer | Class name of the row group footer element |
| p-datatable-empty-message | Class name of the empty message element |
| p-datatable-reorderable-row-handle | Class name of the reorderable row handle element |
| p-datatable-row-editor-init | Class name of the row editor init element |
| p-datatable-row-editor-save | Class name of the row editor save element |
| p-datatable-row-editor-cancel | Class name of the row editor cancel element |
| p-datatable-tfoot | Class name of the tfoot element |
| p-datatable-virtualscroller-spacer | Class name of the virtual scroller spacer element |
| p-datatable-footer | Class name of the footer element |
| p-datatable-column-resize-indicator | Class name of the column resize indicator element |
| p-datatable-row-reorder-indicator-up | Class name of the row reorder indicator up element |
| p-datatable-row-reorder-indicator-down | Class name of the row reorder indicator down element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| datatable.transition.duration | --p-datatable-transition-duration | Transition duration of root |
| datatable.border.color | --p-datatable-border-color | Border color of root |
| datatable.header.background | --p-datatable-header-background | Background of header |
| datatable.header.border.color | --p-datatable-header-border-color | Border color of header |
| datatable.header.color | --p-datatable-header-color | Color of header |
| datatable.header.border.width | --p-datatable-header-border-width | Border width of header |
| datatable.header.padding | --p-datatable-header-padding | Padding of header |
| datatable.header.sm.padding | --p-datatable-header-sm-padding | Sm padding of header |
| datatable.header.lg.padding | --p-datatable-header-lg-padding | Lg padding of header |
| datatable.header.cell.background | --p-datatable-header-cell-background | Background of header cell |
| datatable.header.cell.hover.background | --p-datatable-header-cell-hover-background | Hover background of header cell |
| datatable.header.cell.selected.background | --p-datatable-header-cell-selected-background | Selected background of header cell |
| datatable.header.cell.border.color | --p-datatable-header-cell-border-color | Border color of header cell |
| datatable.header.cell.color | --p-datatable-header-cell-color | Color of header cell |
| datatable.header.cell.hover.color | --p-datatable-header-cell-hover-color | Hover color of header cell |
| datatable.header.cell.selected.color | --p-datatable-header-cell-selected-color | Selected color of header cell |
| datatable.header.cell.gap | --p-datatable-header-cell-gap | Gap of header cell |
| datatable.header.cell.padding | --p-datatable-header-cell-padding | Padding of header cell |
| datatable.header.cell.focus.ring.width | --p-datatable-header-cell-focus-ring-width | Focus ring width of header cell |
| datatable.header.cell.focus.ring.style | --p-datatable-header-cell-focus-ring-style | Focus ring style of header cell |
| datatable.header.cell.focus.ring.color | --p-datatable-header-cell-focus-ring-color | Focus ring color of header cell |
| datatable.header.cell.focus.ring.offset | --p-datatable-header-cell-focus-ring-offset | Focus ring offset of header cell |
| datatable.header.cell.focus.ring.shadow | --p-datatable-header-cell-focus-ring-shadow | Focus ring shadow of header cell |
| datatable.header.cell.sm.padding | --p-datatable-header-cell-sm-padding | Sm padding of header cell |
| datatable.header.cell.lg.padding | --p-datatable-header-cell-lg-padding | Lg padding of header cell |
| datatable.column.title.font.weight | --p-datatable-column-title-font-weight | Font weight of column title |
| datatable.column.title.font.size | --p-datatable-column-title-font-size | Font size of column title |
| datatable.row.background | --p-datatable-row-background | Background of row |
| datatable.row.hover.background | --p-datatable-row-hover-background | Hover background of row |
| datatable.row.selected.background | --p-datatable-row-selected-background | Selected background of row |
| datatable.row.color | --p-datatable-row-color | Color of row |
| datatable.row.hover.color | --p-datatable-row-hover-color | Hover color of row |
| datatable.row.selected.color | --p-datatable-row-selected-color | Selected color of row |
| datatable.row.focus.ring.width | --p-datatable-row-focus-ring-width | Focus ring width of row |
| datatable.row.focus.ring.style | --p-datatable-row-focus-ring-style | Focus ring style of row |
| datatable.row.focus.ring.color | --p-datatable-row-focus-ring-color | Focus ring color of row |
| datatable.row.focus.ring.offset | --p-datatable-row-focus-ring-offset | Focus ring offset of row |
| datatable.row.focus.ring.shadow | --p-datatable-row-focus-ring-shadow | Focus ring shadow of row |
| datatable.row.striped.background | --p-datatable-row-striped-background | Striped background of row |
| datatable.body.cell.border.color | --p-datatable-body-cell-border-color | Border color of body cell |
| datatable.body.cell.padding | --p-datatable-body-cell-padding | Padding of body cell |
| datatable.body.cell.sm.padding | --p-datatable-body-cell-sm-padding | Sm padding of body cell |
| datatable.body.cell.lg.padding | --p-datatable-body-cell-lg-padding | Lg padding of body cell |
| datatable.body.cell.selected.border.color | --p-datatable-body-cell-selected-border-color | Selected border color of body cell |
| datatable.body.cell.font.weight | --p-datatable-body-cell-font-weight | Font weight of body cell |
| datatable.body.cell.font.size | --p-datatable-body-cell-font-size | Font size of body cell |
| datatable.footer.cell.background | --p-datatable-footer-cell-background | Background of footer cell |
| datatable.footer.cell.border.color | --p-datatable-footer-cell-border-color | Border color of footer cell |
| datatable.footer.cell.color | --p-datatable-footer-cell-color | Color of footer cell |
| datatable.footer.cell.padding | --p-datatable-footer-cell-padding | Padding of footer cell |
| datatable.footer.cell.sm.padding | --p-datatable-footer-cell-sm-padding | Sm padding of footer cell |
| datatable.footer.cell.lg.padding | --p-datatable-footer-cell-lg-padding | Lg padding of footer cell |
| datatable.column.footer.font.weight | --p-datatable-column-footer-font-weight | Font weight of column footer |
| datatable.column.footer.font.size | --p-datatable-column-footer-font-size | Font size of column footer |
| datatable.footer.background | --p-datatable-footer-background | Background of footer |
| datatable.footer.border.color | --p-datatable-footer-border-color | Border color of footer |
| datatable.footer.color | --p-datatable-footer-color | Color of footer |
| datatable.footer.border.width | --p-datatable-footer-border-width | Border width of footer |
| datatable.footer.padding | --p-datatable-footer-padding | Padding of footer |
| datatable.footer.sm.padding | --p-datatable-footer-sm-padding | Sm padding of footer |
| datatable.footer.lg.padding | --p-datatable-footer-lg-padding | Lg padding of footer |
| datatable.drop.point.color | --p-datatable-drop-point-color | Color of drop point |
| datatable.column.resizer.width | --p-datatable-column-resizer-width | Width of column resizer |
| datatable.resize.indicator.width | --p-datatable-resize-indicator-width | Width of resize indicator |
| datatable.resize.indicator.color | --p-datatable-resize-indicator-color | Color of resize indicator |
| datatable.sort.icon.color | --p-datatable-sort-icon-color | Color of sort icon |
| datatable.sort.icon.hover.color | --p-datatable-sort-icon-hover-color | Hover color of sort icon |
| datatable.sort.icon.size | --p-datatable-sort-icon-size | Size of sort icon |
| datatable.loading.icon.size | --p-datatable-loading-icon-size | Size of loading icon |
| datatable.row.toggle.button.hover.background | --p-datatable-row-toggle-button-hover-background | Hover background of row toggle button |
| datatable.row.toggle.button.selected.hover.background | --p-datatable-row-toggle-button-selected-hover-background | Selected hover background of row toggle button |
| datatable.row.toggle.button.color | --p-datatable-row-toggle-button-color | Color of row toggle button |
| datatable.row.toggle.button.hover.color | --p-datatable-row-toggle-button-hover-color | Hover color of row toggle button |
| datatable.row.toggle.button.selected.hover.color | --p-datatable-row-toggle-button-selected-hover-color | Selected hover color of row toggle button |
| datatable.row.toggle.button.size | --p-datatable-row-toggle-button-size | Size of row toggle button |
| datatable.row.toggle.button.border.radius | --p-datatable-row-toggle-button-border-radius | Border radius of row toggle button |
| datatable.row.toggle.button.focus.ring.width | --p-datatable-row-toggle-button-focus-ring-width | Focus ring width of row toggle button |
| datatable.row.toggle.button.focus.ring.style | --p-datatable-row-toggle-button-focus-ring-style | Focus ring style of row toggle button |
| datatable.row.toggle.button.focus.ring.color | --p-datatable-row-toggle-button-focus-ring-color | Focus ring color of row toggle button |
| datatable.row.toggle.button.focus.ring.offset | --p-datatable-row-toggle-button-focus-ring-offset | Focus ring offset of row toggle button |
| datatable.row.toggle.button.focus.ring.shadow | --p-datatable-row-toggle-button-focus-ring-shadow | Focus ring shadow of row toggle button |
| datatable.filter.inline.gap | --p-datatable-filter-inline-gap | Inline gap of filter |
| datatable.filter.overlay.select.background | --p-datatable-filter-overlay-select-background | Overlay select background of filter |
| datatable.filter.overlay.select.border.color | --p-datatable-filter-overlay-select-border-color | Overlay select border color of filter |
| datatable.filter.overlay.select.border.radius | --p-datatable-filter-overlay-select-border-radius | Overlay select border radius of filter |
| datatable.filter.overlay.select.color | --p-datatable-filter-overlay-select-color | Overlay select color of filter |
| datatable.filter.overlay.select.shadow | --p-datatable-filter-overlay-select-shadow | Overlay select shadow of filter |
| datatable.filter.overlay.popover.background | --p-datatable-filter-overlay-popover-background | Overlay popover background of filter |
| datatable.filter.overlay.popover.border.color | --p-datatable-filter-overlay-popover-border-color | Overlay popover border color of filter |
| datatable.filter.overlay.popover.border.radius | --p-datatable-filter-overlay-popover-border-radius | Overlay popover border radius of filter |
| datatable.filter.overlay.popover.color | --p-datatable-filter-overlay-popover-color | Overlay popover color of filter |
| datatable.filter.overlay.popover.shadow | --p-datatable-filter-overlay-popover-shadow | Overlay popover shadow of filter |
| datatable.filter.overlay.popover.padding | --p-datatable-filter-overlay-popover-padding | Overlay popover padding of filter |
| datatable.filter.overlay.popover.gap | --p-datatable-filter-overlay-popover-gap | Overlay popover gap of filter |
| datatable.filter.rule.border.color | --p-datatable-filter-rule-border-color | Rule border color of filter |
| datatable.filter.constraint.list.padding | --p-datatable-filter-constraint-list-padding | Constraint list padding of filter |
| datatable.filter.constraint.list.gap | --p-datatable-filter-constraint-list-gap | Constraint list gap of filter |
| datatable.filter.constraint.focus.background | --p-datatable-filter-constraint-focus-background | Constraint focus background of filter |
| datatable.filter.constraint.selected.background | --p-datatable-filter-constraint-selected-background | Constraint selected background of filter |
| datatable.filter.constraint.selected.focus.background | --p-datatable-filter-constraint-selected-focus-background | Constraint selected focus background of filter |
| datatable.filter.constraint.color | --p-datatable-filter-constraint-color | Constraint color of filter |
| datatable.filter.constraint.focus.color | --p-datatable-filter-constraint-focus-color | Constraint focus color of filter |
| datatable.filter.constraint.selected.color | --p-datatable-filter-constraint-selected-color | Constraint selected color of filter |
| datatable.filter.constraint.selected.focus.color | --p-datatable-filter-constraint-selected-focus-color | Constraint selected focus color of filter |
| datatable.filter.constraint.separator.border.color | --p-datatable-filter-constraint-separator-border-color | Constraint separator border color of filter |
| datatable.filter.constraint.padding | --p-datatable-filter-constraint-padding | Constraint padding of filter |
| datatable.filter.constraint.border.radius | --p-datatable-filter-constraint-border-radius | Constraint border radius of filter |
| datatable.paginator.top.border.color | --p-datatable-paginator-top-border-color | Border color of paginator top |
| datatable.paginator.top.border.width | --p-datatable-paginator-top-border-width | Border width of paginator top |
| datatable.paginator.bottom.border.color | --p-datatable-paginator-bottom-border-color | Border color of paginator bottom |
| datatable.paginator.bottom.border.width | --p-datatable-paginator-bottom-border-width | Border width of paginator bottom |

## Column API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| columnKey | string | - | Identifier of a column if field property is not defined. |
| field | string \| Function | - | Property represented by the column. |
| sortField | string \| Function | - | Property name to use in sorting, defaults to field. |
| filterField | string \| Function | - | Property name to use in filtering, defaults to field. |
| dataType | string | - | Type of data. It's value is related to PrimeVue.filterMatchModeOptions config. |
| sortable | boolean | false | Defines if a column is sortable. |
| header | string | - | Header content of the column. |
| footer | string | - | Footer content of the column. |
| style | any | - | Inline style of header, body and footer cells. |
| class | any | - | Style class of header, body and footer cells. |
| headerStyle | any | - | Inline style of the column header. |
| headerClass | any | - | Style class of the column header. |
| bodyStyle | any | - | Inline style of the column body. |
| bodyClass | any | - | Style class of the column body. |
| footerStyle | any | - | Inline style of the column footer. |
| footerClass | any | - | Style class of the column footer. |
| showFilterMenu | boolean | true | Whether to display the filter overlay. |
| showFilterOperator | boolean | true | When enabled, match all and match any operator selector is displayed. |
| showClearButton | boolean | false | Displays a button to clear the column filtering. |
| showApplyButton | boolean | true | Displays a button to apply the column filtering. |
| showFilterMatchModes | boolean | true | Whether to show the match modes selector. |
| showAddButton | boolean | true | When enabled, a button is displayed to add more rules. |
| filterMatchModeOptions | ColumnFilterMatchModeOptions[] | - | An array of label-value pairs to override the global match mode options. |
| maxConstraints | number | 2 | Maximum number of constraints for a column filter. |
| excludeGlobalFilter | boolean | false | Whether to exclude from global filtering or not. |
| filterHeaderStyle | any | - | Inline style of the column filter header in row filter display. |
| filterHeaderClass | any | - | Style class of the column filter header in row filter display. |
| filterMenuStyle | any | - | Inline style of the column filter overlay. |
| filterMenuClass | any | - | Style class of the column filter overlay. |
| selectionMode | any | - | Defines column based selection mode. |
| expander | boolean | false | Displays an icon to toggle row expansion. |
| colspan | number | - | Number of columns to span for grouping. |
| rowspan | number | - | Number of rows to span for grouping. |
| rowReorder | boolean | false | Whether this column displays an icon to reorder the rows. |
| rowReorderIcon | string | - | Icon of the drag handle to reorder rows. |
| reorderableColumn | boolean | false | Defines if the column itself can be reordered with dragging. |
| rowEditor | boolean | false | When enabled, column displays row editor controls. |
| frozen | boolean | false | Whether the column is fixed in horizontal scrolling. |
| alignFrozen | any | left | Position of a frozen column, valid values are left and right. |
| exportable | boolean | false | Whether the column is included in data export. |
| exportHeader | string | - | Custom export header of the column to be exported as CSV. |
| exportFooter | string | - | Custom export footer of the column to be exported as CSV. |
| filterMatchMode | string | - | Defines the filtering algorithm to use when searching the options. |
| hidden | boolean | false | Whether the column is rendered. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ColumnPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| headerCell | ColumnPassThroughOptionType | Used to pass attributes to the header cell's DOM element. |
| columnResizer | ColumnPassThroughOptionType | Used to pass attributes to the column resizer's DOM element. |
| columnHeaderContent | ColumnPassThroughOptionType | Used to pass attributes to the column header content's DOM element. |
| columnTitle | ColumnPassThroughOptionType | Used to pass attributes to the header title's DOM element. |
| sort | ColumnPassThroughOptionType | Used to pass attributes to the sort's DOM element. |
| sortIcon | ColumnPassThroughOptionType | Used to pass attributes to the sort icon's DOM element. |
| pcSortBadge | any | Used to pass attributes to the Badge component. |
| pcHeaderCheckbox | any | Used to pass attributes to the Checkbox component. |
| filter | ColumnPassThroughOptionType | Used to pass attributes to the column filter's DOM element. |
| filterElementContainer | ColumnPassThroughOptionType | Used to pass attributes to the filter element container's DOM element. |
| pcColumnFilterButton | ColumnPassThroughOptionType | Used to pass attributes to the column filter button's DOM element. |
| filterMenuIcon | ColumnPassThroughOptionType | Used to pass attributes to the filter menu icon's DOM element. |
| pcColumnFilterClearButton | ColumnPassThroughOptionType | Used to pass attributes to the column filter clear button's DOM element. |
| filterClearIcon | ColumnPassThroughOptionType | Used to pass attributes to the filter clear icon's DOM element. |
| filterOverlay | ColumnPassThroughOptionType | Used to pass attributes to the filter overlay's DOM element. |
| filterConstraintList | ColumnPassThroughOptionType | Used to pass attributes to the filter constraint list's DOM element. |
| filterConstraint | ColumnPassThroughOptionType | Used to pass attributes to the filter constraint's DOM element. |
| filterConstraintSeparator | ColumnPassThroughOptionType | Used to pass attributes to the filter constraint separator's DOM element. |
| filterOperator | ColumnPassThroughOptionType | Used to pass attributes to the filter operator's DOM element. |
| pcFilterOperatorDropdown | any | Used to pass attributes to the Select component. |
| filterRuleList | ColumnPassThroughOptionType | Used to pass attributes to the filter rule list' DOM element. |
| filterRule | ColumnPassThroughOptionType | Used to pass attributes to the filter rule's DOM element. |
| pcFilterConstraintDropdown | any | Used to pass attributes to the Select component. |
| filterRemove | ColumnPassThroughOptionType | Used to pass attributes to the filter remove button container's DOM element. |
| pcFilterRemoveRuleButton | any | Used to pass attributes to the Button component. |
| filterAddButtonContainer | ColumnPassThroughOptionType | Used to pass attributes to the filter add button container's DOM element. |
| pcFilterAddRuleButton | any | Used to pass attributes to the Button component. |
| filterButtonbar | ColumnPassThroughOptionType | Used to pass attributes to the filter buttonbar's DOM element. |
| pcFilterClearButton | any | Used to pass attributes to the Button component. |
| pcFilterApplyButton | any | Used to pass attributes to the Button component. |
| rowToggleButton | ColumnPassThroughOptionType | Used to pass attributes to the row toggler button's DOM element. |
| rowToggleIcon | ColumnPassThroughOptionType | Used to pass attributes to the row toggler icon's DOM element. |
| nodeToggleButton | ColumnPassThroughOptionType | Used to pass attributes to the node toggle button's DOM element. |
| nodeToggleIcon | ColumnPassThroughOptionType | Used to pass attributes to the node toggle icon's DOM element. |
| bodyCell | ColumnPassThroughOptionType | Used to pass attributes to the body cell's DOM element. |
| reorderableRowHandle | ColumnPassThroughOptionType | Used to pass attributes to the reorderable row handle's DOM element. |
| pcRowRadiobutton | any | Used to pass attributes to the radiobutton's DOM element. |
| pcRowCheckbox | any | Used to pass attributes to the checkbox's DOM element. |
| pcNodeCheckbox | any | Used to pass attributes to the node checkbox's DOM element. |
| pcRowEditorInit | ColumnPassThroughOptionType | Used to pass attributes to the row editor init button's DOM element. |
| pcRowEditorSave | ColumnPassThroughOptionType | Used to pass attributes to the row editor save button's DOM element. |
| pcRowEditorCancel | ColumnPassThroughOptionType | Used to pass attributes to the row editor cancel button's DOM element. |
| footerCell | ColumnPassThroughOptionType | Used to pass attributes to the footer cell's DOM element. |
| columnFooter | ColumnPassThroughOptionType | Used to pass attributes to the footer content DOM element. |
| bodyCellContent | ColumnPassThroughOptionType | Used to pass attributes to the body cell content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

## Column Group API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| type | any | - | Type of column group |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ColumnGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

## Row API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | RowPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

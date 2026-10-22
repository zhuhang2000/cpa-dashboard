<template>
  <div class="input-group">
    <input v-model="password" v-bind="$attrs" class="input" :type="visible ? 'text' : 'password'" />
    <button
      type="button"
      class="input-addon"
      :aria-label="visible ? '隐藏密码' : '显示密码'"
      @click="visible = !visible"
    >
      <Icon :name="visible ? 'eye-off' : 'eye'" :size="16" />
    </button>
  </div>
</template>

<script setup>
import Icon from './Icon.vue'

// id, autocomplete, placeholder, required and the like belong on the <input>, not the wrapper.
defineOptions({ inheritAttrs: false })
const password = defineModel({ type: String, default: '' })
// Bind v-model:visible when another field (such as a confirmation) should show and hide with this one.
const visible = defineModel('visible', { type: Boolean, default: false })
</script>

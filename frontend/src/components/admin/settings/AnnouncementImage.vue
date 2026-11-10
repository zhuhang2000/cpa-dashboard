<template>
  <div class="field">
    <label :for="inputId">公告图片</label>
    <input
      :id="inputId"
      v-model.trim="url"
      class="input mono"
      type="url"
      pattern="https://.+"
      maxlength="500"
      placeholder="https://example.com/promo.png"
    />
    <div class="field-hint">填写 https 图片链接（如 R2 公开地址），显示在用户概览页顶部；留空则不显示</div>
    <template v-if="url">
      <div v-if="failed" class="field-hint text-danger">图片加载失败，请检查链接是否可公开访问</div>
      <template v-else>
        <div class="ann-size">
          <label :for="sizeId">显示宽度</label>
          <input
            :id="sizeId"
            type="range"
            min="160"
            :max="MAX_WIDTH"
            step="10"
            :value="shown"
            @input="width = Number($event.target.value)"
          />
          <span class="num">{{ shown }} × {{ shownHeight ?? '–' }} px</span>
        </div>
        <AnnouncementBanner :url="url" :width="width" @load="measure" @error="failed = true" />
        <div class="field-hint">
          高度按图片比例自动计算，不会拉伸。概览页内容区最宽约
          {{ MAX_WIDTH }} px；预览和窄屏（如手机）上放不下时等比缩小
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, useId, watch } from 'vue'
import AnnouncementBanner, { DEFAULT_WIDTH } from '@/components/shared/AnnouncementBanner.vue'

// The overview's content width at its widest (1320px less the page padding).
const MAX_WIDTH = 1270

// The picture is hosted elsewhere (e.g. R2): the settings keep its URL ('' for none) and its shown width
// in px (0 for the banner's default).
const url = defineModel('url', { type: String, required: true })
const width = defineModel('width', { type: Number, required: true })
const inputId = useId()
const sizeId = useId()
const failed = ref(false)
const ratio = ref(null)

const shown = computed(() => width.value || DEFAULT_WIDTH)
const shownHeight = computed(() => ratio.value && Math.round(shown.value / ratio.value))

watch(url, () => {
  failed.value = false
  ratio.value = null
})

function measure(event) {
  ratio.value = event.target.naturalWidth / event.target.naturalHeight
}
</script>

<style scoped>
.ann-size {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: var(--text-2);
}
.ann-size input {
  flex: 1;
  min-width: 0;
  accent-color: var(--accent);
}
.ann-size .num {
  flex: none;
  color: var(--muted);
}
</style>

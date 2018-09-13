<template>
  <div 
    class="item"
    :class="item.state">
      <div class="top">
        <h3>
          {{ item.sub }} <small>⮀</small> 
          {{ item.task }} <small>⮀</small> 
          {{ typestext[item.type] }} 
          <template v-if="item.run !== undefined && item.run.length > 0"> <small>⮀</small> {{ item.run }} </template> 
        </h3>
        <button 
          class="button good"
          @click="setstategood">😍</button>
        <button 
          class="button ok"
          @click="setstateok">😕</button>
        <button 
          class="button bad"
          @click="setstatebad">😨</button>
      </div>
      <div 
        class="content" 
        v-html="html">
      </div>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "item",
  mounted() {
    axios
      .get(this.item.fname, { 
        responseType: "text",
      }).then(response => {
        const html = new DOMParser().parseFromString(
          response.data,
          "image/svg+xml"
        );
        html.documentElement.removeAttribute("width");
        html.documentElement.removeAttribute("height");
        this.html = new XMLSerializer().serializeToString(html);
      });
  },
  props: [
    "item",
    "typestext",
  ],
  data() {
    return {
      html: "",
    };
  },
  computed: {},
  methods: {
    setstategood() {
      this.item.state = 
        "good";
      this.$forceUpdate();
    },
    setstateok() {
      this.item.state =
        "ok";
      this.$forceUpdate();
    },
    setstatebad() {
      this.item.state =
        "bad";
      this.$forceUpdate();
    }
  }
};
</script>

<style scoped>
.item {
  position: relative;

  display: flex;
  flex-direction: column;

  overflow: hidden;
  width: 100%;

  border-bottom: 1px solid rgb(36, 63, 215);
}
.item.good {
  background-color: rgba(35, 209, 96, 0.5);
}
.item.ok {
  background-color: rgba(255, 221, 87, 0.5);
}
.item.bad {
  background-color: rgba(252, 123, 207, 0.5);
}
.item .top {
  display: inline-block;
  flex: none;

  width: 100%;

  height: 2.5rem;
  padding: 0.25rem;
}
.item .top h3 {
  display: inline-block;

  vertical-align: middle;

  font-weight: bold;
  font-size: 1rem;
  padding: 0.5rem;
}
.item .top button {
  -moz-appearance: none;
  -webkit-appearance: none;

  border: none;

  display: inline-block;

  font-size: 2rem;
  line-height: 1;
  height: auto;

  background-color: transparent;

  padding: 0.25rem 0.2rem 0.15rem 0.2rem;
  margin-left: 1rem;

  opacity: 0.5;
}
.item.good .top button.good {
  opacity: 1;
}
.item.ok .top button.ok {
  opacity: 1;
}
.item.bad .top button.bad {
  opacity: 1;
}
</style>
<style>
.content svg {
  height: calc(100vh - 9.5rem) !important;
  max-width: 100%;
}
.content svg > * {
  background-color: white;
}
.content svg .foreground-svg {
  animation-play-state: running !important;
}
</style>

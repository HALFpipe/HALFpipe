<template>
  <button 
    class="button"
    :class="[state, { active: isActive }]">
    <a>{{ text }}</a>
    <div 
      class="progress" 
      :style="{ width: progresspercent + '%' }"></div>
  </button>
</template>

<script>
export default {
  name: "navbutton",
  mounted() {
  },
  props: [
    "i", 
    "field",
    "text",
    "progresspercent",
    "isActive",
  ],
  data() {
    return {
      
    };
  },
  computed: {
    state() {
      if (this.progresspercent > 99.99) {
        return("good");
      }
      return("");
    },
  },
  methods: {
  }
};
</script>

<style scoped>
button {
  position: relative;

  display: inline-block !important;

  color: rgb(36, 63, 215);
  background: transparent;
  border-color: rgb(36, 63, 215);

  margin: 0 1.5rem 0 0.15rem;
}

button.good {
  color: rgb(42, 224, 161);
  border-color: rgb(42, 224, 161);
}

button.active {
  font-weight: bold;
}

button a {
  color: inherit;
  position: relative;
  z-index: 100;
}

button .progress {
  position: absolute;
  top: 0;
  left: 0;

  width: 0;
  height: 100%;

  border-radius: 0;

  background-color: rgb(129, 147, 255);

  opacity: 0.75;
}

button.good .progress {
  background-color: rgb(162, 255, 225);
}

button::after {
  content: "⮀";
  position: absolute;
  top: 0.3rem;

  margin-left: 1.33rem;
}
button:last-child::after {
  display: none;
}
</style>

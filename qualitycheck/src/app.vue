<template>
  <div>
    <header>
      mindandbrain pipeline 0.0.6-dev quality check
    </header>
    <itemlist ref="itemlist" :itemsby="itemsby" 
      :complete="complete" :total="total"></itemlist>
  </div>
</template>

<script>
import itemlist from "./components/itemlist.vue";
import axios from "axios";

import types from "./types.js";
const tagtotypemap = types.reduce((m, o, i) => {
  m[o.tag] = i;
  return m;
}, {});

export default {
  name: "app",
  components: {
    itemlist
  },
  data() {
    return {
      items: [],
      itemsby: {
        sub: [],
        type: [],
      },
      complete: {},
    };
  },
  mounted() {
    axios
      .get("qc.json")
      .then(response => {
        this.items = response.data.map(item => {
          const parts = item.id.split(".");
          item.sub = parts.find(part => part.startsWith("sub-"));
          if (item.sub !== undefined) {
            item.sub = item.sub.substring("sub-".length);
          }
          item.task = parts.find(part => part.startsWith("task-"));
          if (item.task !== undefined) {
            item.task = item.task.substring("task-".length);
          }
          item.run = parts.find(part => part.startsWith("run-"));
          if (item.run !== undefined) {
            item.run = item.run.substring("run-".length);
          }

          item.tag = parts.filter(part => !part.startsWith("sub-") && 
            !part.startsWith("task-") && !part.startsWith("run-")).join(".");
          if (item.task === undefined && item.tag.startsWith("T1w")) {
            item.task = "T1w";
          }
          
          item.type = tagtotypemap[item.tag];
          
          if (item.type === undefined) {
            return(item);
          }
          
          item.key = item.sub + "#" + types[item.type].tag + "#" + item.task;
          if (item.run !== undefined) {
            item.key += "#" + item.run;
          }
          
          var self = this;
          item.oncomplete = () => {
            if (self.complete[item.sub] === undefined) {
              self.complete[item.sub] = 0;
            }
            self.complete[item.sub]++;
            
            if (self.complete[item.type] === undefined) {
              self.complete[item.type] = 0;
            }
            self.complete[item.type]++;
            item._complete = true;
          };
          
          Object.defineProperty(item, "state", { 
            set: function(value) {
              if (this._complete === undefined) {
                this.oncomplete();
              }
              localStorage.setItem(this.key, value);
              self.$refs.itemlist.$forceUpdate();
            },
            get: function() {
              return(localStorage.getItem(this.key));
            },
          });

          return(item);
        }).filter(item => {
          return(item.type !== undefined)
        });
        
        this.items.forEach(item => {
          var state = localStorage.getItem(item.key);
          if (state !== null && state !== "null") {
            item.state = state;
          }
        });
        
        let compareFunction = (a, b) => {
          if (a < b) {
            return -1;
          } else if (a > b) {
            return 1;
          } else {
            return 0;
          }
        };
        this.itemsby.sub = this.items.slice(0).sort((a, b) => {
          if (a.sub === b.sub) {
            if (a.type === b.type) {
              if (a.task == b.task) {
                return compareFunction(a.run, b.run);
              }
              return compareFunction(a.task, b.task);
            } 
            return compareFunction(a.type, b.type);
          } 
          return compareFunction(a.sub, b.sub);
        });
        this.itemsby.type = this.items.slice(0).sort((a, b) => {
          if (a.type === b.type) {
            if (a.sub === b.sub) {
              if (a.task == b.task) {
                return compareFunction(a.run, b.run);
              }
              return compareFunction(a.task, b.task);
            } 
            return compareFunction(a.sub, b.sub);
          } 
          return compareFunction(a.type, b.type);
        });
      });  
      
      this.$refs.itemlist.onscroll();
      setInterval(this.$refs.itemlist.onscroll, 1000);
      
      if (window.location.hash) {
        this.$refs.itemlist.gotohash();
      }
  },
  computed: {
    total() {
      const total = {};
      
      this.items.forEach(function(item) {
        if (total[item.sub] === undefined) {
          total[item.sub] = 0;
        }
        total[item.sub]++;
        if (total[item.type] === undefined) {
          total[item.type] = 0;
        }
        total[item.type]++;
      });
      
      return(total);
    },
  },
  methods: {
  }
};
</script>

<style lang="sass"> 
@charset "utf-8";

$desktop: 100px;

@import "../node_modules/bulma/bulma.sass";
</style>
<style>
body {
  overflow: hidden;
}
#app {
  font-family: "Avenir", Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;

  overflow: hidden;
}
header {
  position: relative;
  top: 0;

  background: rgb(36, 63, 215);
  background: linear-gradient(
    180deg,
    rgba(36, 63, 215, 1) 0%,
    rgba(34, 60, 203, 1) 100%
  );

  color: white;

  height: 1.5rem;
  font-size: 0.7rem;
  padding: 0.25rem;
}
header a {
  color: white !important;
  position: absolute;
  right: 0.25rem;
}
</style>

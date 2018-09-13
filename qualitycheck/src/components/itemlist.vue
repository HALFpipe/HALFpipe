<template>
  <div>
    <nav class="navbar">
      <div class="navbar-start">
        <a class="navbar-item" @click="toggle" v-if="false">
          Summary
        </a>
        <div class="navbar-item has-dropdown is-hoverable" v-if="!showsummary">
          <a class="navbar-link">
            Sort by
          </a>
          <div class="navbar-dropdown">
            <a class="navbar-item" @click="setby('sub')">
              Subject
            </a>
            <a class="navbar-item" @click="setby('type')">
              Type
            </a>
          </div>
        </div>
      </div>
      <div class="navbar-item buttongroupwrapper" v-if="!showsummary">
        <div class="buttongroup" :class="{ visible: field === 'sub' }" 
          :style="{ left: getoffset('sub') + 'px' }"
          ref="subnavbuttongroup">
          <template 
            v-for="sub of allsubs">
            <navbutton 
              :key="sub" 
              :i="sub" :text="sub" field="sub" 
              :progresspercent="complete[sub] / total[sub] * 100."
              :isActive="currentsub === sub"
              ref="subnavbutton"
              @click.native="gotosub(sub)"></navbutton>
          </template>
        </div>
        <div class="buttongroup" :class="{ visible: field === 'type' }"
          :style="{ left: getoffset('type') + 'px' }"
          ref="typenavbuttongroup">
          <template 
            v-for="type of alltypes">
            <navbutton 
              :key="type"
              :i="type" :text="typestext[type]" field="type" 
              :isActive="currenttype === type"
              :progresspercent="complete[type] / total[type] * 100."
              ref="typenavbutton"
              @click.native="gototype(type)"></navbutton>
          </template>
        </div>
      </div>
      <div class="navbar-end">
        <a class="navbar-item" @click="download" ref="download" href="#" target="_blank" download="qcresult.json">
          Download
        </a>  
      </div>
    </nav>
    <main
      ref="main"
      class="itemlist"
      @scroll.passive="onscroll"
      v-if="!showsummary">
        <div 
          class="itemwrapper"
          :style="{ height: itemsby[field].length*individualheight + 'px' }">
            <div
              v-for="view of views"
              v-if="view.inuse"
              :key="view.viewid"
              :style="{ height: individualheight + 
                'px', transform: 'translateY(' + (view.i*individualheight) + 'px)' }"
              class="itemview">
                <item 
                  ref="item"
                  :style="{ height: individualheight + 'px' }"
                  :item="itemsby[field][view.i]"
                  :typestext="typestext">
                </item>
          </div>
        </div>
    </main>
    <div
      ref="summary"
      class="summary"
      v-if="showsummary">
      
    </div>
  </div>
  
</template>

<script>
import item from "./item.vue";
import navbutton from "./navbutton.vue";

import types from "../types.js";
const typestext = types.map(t => {
  return t.type;
});

export default {
  name: "itemlist",
  components: {
    item,
    navbutton
  },
  created() {
    this.previousi = null;
    this.scrolldirty = false;
    this.hashdirty = false;
  },
  mounted() {
    window.addEventListener("resize", this.onresize);
    window.addEventListener("hashchange", this.onhashchange);
    window.addEventListener("keyup", this.onkeyup);
  },
  beforeDestroy() {
    window.removeEventListener("resize", this.onresize);
    window.removeEventListener("hashchange", this.onhashchange);
  },
  data() {
    return {
      views: [],
      types: [],
      field: "type",
      individualheight: 1,
      typestext: typestext,
      currentsub: "",
      currenttype: 0,
      showsummary: false,
    };
  },
  props: [
    "itemsby",
    "complete",
    "total",
  ],
  computed: {
    alltypes() {
      return([...new Set(this.itemsby.type.map(item => item.type))]);
    },
    allsubs() {
      return([...new Set(this.itemsby.sub.map(item => item.sub))]);
    },
    indexby() {
      const x = {
        type: {},
        sub: {},
      };
      
      this.itemsby.sub.forEach((item, i) => {
        if (x.sub[item.sub] === undefined) {
          x.sub[item.sub] = {};
        }
        if (x.sub[item.sub][item.type] === undefined) {
          x.sub[item.sub][item.type] = {};
        }
        if (x.sub[item.sub][item.type][item.task] === undefined) {
          x.sub[item.sub][item.type][item.task] = {};
        }
        if (x.sub[item.sub][item.type][item.task][item.run] === undefined) {
          x.sub[item.sub][item.type][item.task][item.run] = {};
        }
        x.sub[item.sub][item.type][item.task][item.run] = i;
      });
      
      this.itemsby.type.forEach((item, i) => {
        if (x.type[item.sub] === undefined) {
          x.type[item.sub] = {};
        }
        if (x.type[item.sub][item.type] === undefined) {
          x.type[item.sub][item.type] = {};
        }
        if (x.type[item.sub][item.type][item.task] === undefined) {
          x.type[item.sub][item.type][item.task] = {};
        }
        if (x.type[item.sub][item.type][item.task][item.run] === undefined) {
          x.type[item.sub][item.type][item.task][item.run] = {};
        }
        x.type[item.sub][item.type][item.task][item.run] = i;
      });
      
      return(x);
    },
    bykey() {
      const x = {};
      this.itemsby.type.forEach(item => {
        x[item.key] = item;
      });
      return(x);
    },
  },
  watch: {},
  methods: {
    // event handlers
    onkeyup(event) {
      try {
        const items = this.itemsby[this.field];
      
        let ic = 0;
        if (this.$refs.main) {
          ic = this.$refs.main.scrollTop;
        }
        ic /= this.individualheight;
        let i0 = Math.floor(ic);
      
        if (event.key === " ") {
          this.$refs.main.scrollTop = this.individualheight * (i0 + 1);
          event.preventDefault();
        } else {
          let item = this.$refs.item.find(v => {
            if (
              v.item.id === items[i0].id &&
              v.item.type === items[i0].type &&
              v.item.scan === items[i0].scan
            ) {
              return true;
            }
            return false;
          });
      
          if (item) {
            if (event.key == "a") {
              item.setstategood();
            } else if (event.key == "s") {
              item.setstateok();
            } else if (event.key == "d") {
              item.setstatebad();
            }
          }
        }
      
        this.update();
      } catch (error) {
        // continue regardless of error
      }
    },
    onresize() {
      this.update();
    },
    onscroll() {
      if (!this.scrolldirty) {
        this.scrolldirty = true;
        requestAnimationFrame(() => {
          this.scrolldirty = false;
          this.update();
        });
      }
    },
    onhashchange(event) {      
      event.preventDefault();
      this.gotohash();
    },
    
    //
    toggle(){
      this.showsummary = !this.showsummary;
    },

    //
    currentitem() {  
      const items = this.itemsby[this.field];
    
      let ic = this.$refs.main.scrollTop /
        this.individualheight;
        
      let i2 = Math.floor(ic + 0.5);
      
      if (i2 < 0) {
        i2 = 0;
      }
      
      const item = items[i2];
      if (item) {
        this.currentsub = item.sub;
        this.currenttype = item.type;
      }
      
      return(item);
    },
    setby(by) {
      if (this.field !== by) {
        this.swap();
      }
    },
    swap() {
      const ci = this.currentitem();
      if (this.field === "type") {
        this.field = "sub";
      } else {
        this.field = "type";
      }
      this.tohash(ci);
      this.gotoitem(ci.sub, ci.type, ci.task, ci.run);
    },
    gotohash() {
      this.hashdirty = true;
      let hash = window.location.hash.substr(1).split("#");
      this.field = hash[0];
      hash.splice(0, 1);
      const ci = this.bykey[hash.join("#")];
      if (ci !== undefined) {
        this.gotoitem(ci.sub, ci.type, ci.task, ci.run);
      } else {
        setTimeout(this.gotohash, 500);
      }
      this.hashdirty = false;
    },
    gototype(type) {
      const ci = this.currentitem();
      this.gotoitem(ci.sub, type, ci.task, ci.run);
    },
    gotosub(sub) {
      const ci = this.currentitem();
      this.gotoitem(sub, ci.type, ci.task, ci.run);
    },
    gotoitem(sub, type, task, run) {
      if (this.$refs.main) {
        const index = this.indexby[this.field];
        
        if (index[sub] === undefined) {
          sub = Object.keys(index)[0];
        } 
        if (index[sub][type] === undefined) {
          type = Object.keys(index[sub])[0];
        } 
        if (index[sub][type][task] === undefined) {
          task = Object.keys(index[sub][type])[0];
        } 
        if (index[sub][type][task][run] === undefined) {
          run = Object.keys(index[sub][type][task])[0];
        } 
        const i0 = index[sub][type][task][run];      
        this.gotoindex(i0);
      }
    },
    gotoindex(i) {
      this.$refs.main.scrollTop = this.individualheight * i;
      this.update();
    },
    tohash(item) {
      if (item) {
        var s = this.field;
        if (this.showsummary) {
          s = "summary";
        }
        history.replaceState(
          "",
          "",
          "#" + s + "#" + item.key,
        );
      }
    },
    
    getoffset(field) {
      if (this.$refs.main && field === this.field) {
        const ci = this.currentitem();
        if (ci) {
          let rect0, rect1, rect2;
          if (field === "sub" && this.$refs.subnavbuttongroup && this.$refs.subnavbutton) {
            const i0 = this.allsubs.findIndex(sub => sub === ci.sub);
            rect0 = this.$refs.subnavbuttongroup.parentElement.getBoundingClientRect();
            rect1 = this.$refs.subnavbuttongroup.getBoundingClientRect();
            rect2 = this.$refs.subnavbutton[i0].$el.getBoundingClientRect();
            
          }
          if (field === "type" && this.$refs.typenavbuttongroup && this.$refs.typenavbutton) {
            const i0 = this.alltypes.findIndex(type => type === ci.type);
            rect0 = this.$refs.typenavbuttongroup.parentElement.getBoundingClientRect();
            rect1 = this.$refs.typenavbuttongroup.getBoundingClientRect();
            rect2 = this.$refs.typenavbutton[i0].$el.getBoundingClientRect();
          }
          if (rect0 && rect1) {
            let l0 = rect1.left-rect2.left;
            l0 += rect0.width / 2;
            l0 -= rect2.width / 2;
            
            return(l0);
          }
        }
      }
      
      return 0;
    },
    
    //
    update() {
      if (!this.$refs.main) {
        return;
      }
      
      this.individualheight = this.$refs.main.clientHeight;

      const items = this.itemsby[this.field];
      
      let ic = this.$refs.main.scrollTop /
        this.individualheight;
      
      let i0 = Math.floor(ic);
      let i1 = Math.ceil(ic) + 2;
      
      if (i0 < 0) {
        i0 = 0;
      }
      
      if (i1 > items.length) {
        i1 = items.length;
      }
      
      // hash
      const i2 = Math.floor(ic + 0.5);
      
      if (items[i2] !== undefined) {
        this.currentsub = items[i2].sub;
        this.currenttype = items[i2].type;
        
        if (this.previousi !== i2 && !this.hashdirty) {
          this.tohash(items[i2]);
          this.previousi = i2;
        }
      }
      
      // itemlist
      const ii = [];
      for (let i = i0; i < i1; i++) {
        ii.push(i);
      }
      
      const inuse = this.views.map(v => {
        if (v.i >= i0 && v.i < i1) {
          ii.splice(ii.indexOf(v.i), 1);
          return true;
        }
        return false;
      });
      
      this.views.forEach((v, i) => {
        if (v.inuse !== inuse[i]) {
          v.inuse = inuse[i];
        }
      });
      
      ii.forEach(i => {
        let j = inuse.indexOf(false);
        let view = this.views[j];
        if (j === -1) {
          view = this.newview();
        }
      
        view.i = i;
        view.item = items[i];
      });
      
      
    },
    newview() {
      let view = {
        i: 0,
        inuse: false
      };
      this.views.push(view);
      return view;
    },
    
    //
    download() {
      const data = {};
      this.itemsby.sub.forEach(item => {
        if (data[item.sub] === undefined) {
          data[item.sub] = {};
        }
        if (data[item.sub][item.task] === undefined) {
          data[item.sub][item.task] = {};
        }
        let run = item.run;
        if (run === undefined) {
          run = "";
        }
        if (data[item.sub][item.task][run] === undefined) {
          data[item.sub][item.task][run] = {};
        }
        data[item.sub][item.task][run][item.tag] = item.state;
      });
      this.$refs.download.setAttribute(
        "href",
        "data:attachment/text," + encodeURI(JSON.stringify(data, null, 2))
      );
    },
  }
};
</script>

<style scoped>
nav {
  position: relative;
  padding: 0;
  
  overflow: visible;
  
  min-height: 3.25rem !important;

  white-space: nowrap; 

  background-color: rgb(255, 255, 255);

  border-bottom: 1px solid rgb(36, 63, 215);
}

nav .navbar-start, nav .navbar-end {
  position: relative;
  overflow: visible;
  z-index: 20000;
  background-color: white;
}

nav div.buttongroup {
  display: none;
  position: relative;
}
nav div.buttongroupwrapper {
  display: block !important;
  position: absolute;
  width: 100%;
  z-index: 2;
}
nav div.navbar-start::before {
  content: "";
  height: 100%;   
  width: 10px; 
  position: absolute;
  right: -10px;
  top: 0;
  background: linear-gradient(to right, white 0%, transparent 100%);
  z-index:10000;
}

nav .navbar-end {
  position:relative;
}
nav .navbar-end::before {
  content: "";
  height: 100%;   
  width: 10px; 
  position: absolute;
  left: -10px;
  top: 0;
  background: linear-gradient(to right, transparent 0%, white 100%);
  z-index:10000;
}

nav div.visible {
  display: inline-block;
  overflow-x: hidden;
}

.itemlist {
  height: calc(100vh - 4.75rem);
  width: 100%;
  overflow-y: scroll;
}
.itemwrapper {
  box-sizing: border-box;
  width: 100%;
  overflow: hidden;
  position: relative;
}
.itemview {
  width: 100%;
  position: absolute;
  top: 0;
  left: 0;
  will-change: transform;
}
</style>

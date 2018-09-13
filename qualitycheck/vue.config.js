var HtmlWebpackInlineSourcePlugin = 
  require('html-webpack-inline-source-plugin');

module.exports = {
  baseUrl: "",
  css: {
    extract: true
  },
  configureWebpack: {
    optimization: {
    },
    plugins: [
      new HtmlWebpackInlineSourcePlugin(),
    ],
  },
  chainWebpack: config => {
    config.plugins.delete("preload");
    config.plugins.delete("prefetch");
    
    if (process.env.NODE_ENV === 'production') {
      config.plugin("html").tap(args => {
        args[0].inlineSource = '.(js|css)$';
        return(args);
      });
    }
  }
};

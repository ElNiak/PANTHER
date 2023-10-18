// get rid of absolute paths in the .html output
// https://github.com/vuejs/vue-cli/issues/1623

module.exports = {
    baseUrl: './',
    configureWebpack: {
        devtool: 'source-map',
        devServer: {
            allowedHosts: ["all"],
            host: '0.0.0.0',
            port: 80,
            disableHostCheck: true,
        }
    }
}

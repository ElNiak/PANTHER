const webpack = require('webpack');const config = {
    entry:  __dirname + '/js/index.jsx',
    output: {
        path: __dirname + '/dist',
        filename: 'bundle.js',
    },
    resolve: {
        extensions: ['.js', '.jsx', '.css']
    },
};module.exports = config;

////https://stackoverflow.com/questions/24514936/how-can-i-serve-npm-packages-using-flask
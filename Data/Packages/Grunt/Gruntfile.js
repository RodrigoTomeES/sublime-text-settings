'use strict'

module.exports = function (grunt) {
  // Project configuration.
  grunt.initConfig({
    eslint: {
      options: {
        configFile: '.eslintrc'
      },
      validate: ['Gruntfile.js', 'expose.js']
    }
  })

  // These plugins provide necessary tasks.
  grunt.loadNpmTasks('grunt-eslint')

  grunt.registerTask('lint', ['eslint'])

  // Default task.
  grunt.registerTask('default', ['lint'])
}

'use strict'

module.exports.register = function () {
  this.on('documentsConverted', ({ contentCatalog }) => {
    contentCatalog.getPages((page) => page.out).forEach((page) => {
      if (page.asciidoc?.attributes['page-unpublish'] != null) {
        delete page.out
      }
    })
  })
}

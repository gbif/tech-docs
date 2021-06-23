;(function () {
  'use strict'

  var toggle = document.querySelector('.page-languages .language-menu-toggle')
  if (!toggle) return

  var selector = document.querySelector('.page-languages')

  toggle.addEventListener('click', function (e) {
    selector.classList.toggle('is-active')
    e.stopPropagation() // trap event
  })

  document.documentElement.addEventListener('click', function () {
    selector.classList.remove('is-active')
  })
})()

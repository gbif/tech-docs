/*
 * Term recommendation explorer.
 *
 * Loaded only on pages that set `:page-termexplorer:` (see partials/head-styles.hbs).
 * Renders into <div id="term-explorer">. Data comes from two CSV files in
 * supplemental_ui/data/term-recommendations/:
 *
 *   guides.csv  guide, element, level, option, group
 *     For one guide + element + level, rows with the same option number belong
 *     together (all their groups apply), and different option numbers are
 *     alternatives (any one of them is enough). Option 1 is the preferred one.
 *
 *   terms.csv   IRI, element, grouping, term_requirement
 *     A grouping is a set of terms. term_requirement says whether the term is
 *     required or only recommended within that set.
 */
(function () {
  'use strict'

  var script = document.currentScript
  var DATA_URL = (script && script.getAttribute('data-data-url')) || '../_/data/term-recommendations/'
  var ENV = (script && script.getAttribute('data-env')) || ''
  var LEVEL_ORDER = ['required', 'recommended', 'share if available']
  var NAMESPACES = [
    { iri: 'http://rs.tdwg.org/dwc/terms/', prefix: 'dwc', label: 'Darwin Core' },
    { iri: 'http://rs.tdwg.org/eco/terms/', prefix: 'eco', label: 'Humboldt Extension' },
    { iri: 'http://rs.tdwg.org/dwc/iri/', prefix: 'dwciri', label: 'Darwin Core IRI' },
    { iri: 'http://purl.org/dc/terms/', prefix: 'dcterms', label: 'Dublin Core' },
  ]
  var GUIDE_COLOURS = 6

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init)
  else init()

  // ---------------------------------------------------------------- loading

  function init () {
    var root = document.getElementById('term-explorer')
    if (!root) return
    root.classList.add('term-explorer')
    root.setAttribute('aria-busy', 'true')
    root.replaceChildren(el('p', { className: 'te-status' }, 'Loading term recommendations…'))

    Promise.all([fetchCSV(DATA_URL + 'terms.csv'), fetchCSV(DATA_URL + 'guides.csv')])
      .then(function (r) {
        var data = buildModel(r[0], r[1])
        root.removeAttribute('aria-busy')
        new Explorer(root, data).start()
      })
      .catch(function (e) {
        root.removeAttribute('aria-busy')
        root.replaceChildren(el('div', { className: 'te-error', role: 'alert' }, [
          el('strong', null, 'The term recommendations could not be loaded. '),
          e.message + ' ',
          'The data is also available as ',
          el('a', { href: DATA_URL + 'guides.csv' }, 'guides.csv'), ' and ',
          el('a', { href: DATA_URL + 'terms.csv' }, 'terms.csv'), '.',
        ]))
        if (window.console) console.error('[term-explorer]', e)
      })
  }

  function fetchCSV (url) {
    return fetch(url, { cache: 'no-cache' }).then(function (res) {
      if (!res.ok) throw new Error('Could not fetch ' + url + ' (HTTP ' + res.status + ').')
      return res.text()
    }).then(parseCSV)
  }

  // RFC 4180-ish parser (quoted fields, escaped quotes, CRLF). Returns array of objects keyed by header.
  function parseCSV (text) {
    text = text.replace(/^﻿/, '')
    var rows = []
    var row = []
    var field = ''
    var inQuotes = false
    for (var i = 0; i < text.length; i++) {
      var c = text[i]
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++ } else inQuotes = false
        } else field += c
      } else if (c === '"') inQuotes = true
      else if (c === ',') { row.push(field.trim()); field = '' } else if (c === '\n') {
        row.push(field.trim()); field = ''
        if (row.some(Boolean)) rows.push(row)
        row = []
      } else if (c !== '\r') field += c
    }
    if (inQuotes) throw new Error('A CSV file contains an unclosed quoted field.')
    row.push(field.trim())
    if (row.some(Boolean)) rows.push(row)
    if (!rows.length) return []
    var headers = rows[0]
    return rows.slice(1).map(function (values) {
      var o = {}
      headers.forEach(function (h, j) { o[h] = (values[j] || '').trim() })
      return o
    })
  }

  // ---------------------------------------------------------------- model

  function requireColumns (rows, cols, name) {
    if (!rows.length) throw new Error(name + ' is empty.')
    var missing = cols.filter(function (c) { return !(c in rows[0]) })
    if (missing.length) throw new Error(name + ' is missing the column(s): ' + missing.join(', ') + '.')
  }

  function buildModel (termRows, guideRows) {
    requireColumns(termRows, ['IRI', 'element', 'grouping', 'term_requirement'], 'terms.csv')
    requireColumns(guideRows, ['guide', 'element', 'level', 'option', 'group'], 'guides.csv')
    var warnings = []

    var termsByGroup = new Map()
    var elements = []
    termRows.forEach(function (r, i) {
      if (!r.IRI || !r.grouping) {
        warnings.push('terms.csv line ' + (i + 2) + ': missing IRI or grouping, row ignored.')
        return
      }
      var t = describeTerm(r.IRI)
      t.element = r.element
      t.group = r.grouping
      t.requirement = (r.term_requirement || 'required').toLowerCase()
      if (!termsByGroup.has(t.group)) termsByGroup.set(t.group, [])
      termsByGroup.get(t.group).push(t)
      if (r.element && elements.indexOf(r.element) < 0) elements.push(r.element)
    })

    var guides = []
    var levels = []
    var recs = []
    guideRows.forEach(function (r, i) {
      var line = 'guides.csv line ' + (i + 2) + ': '
      if (!r.guide || !r.element || !r.level || !r.group) {
        warnings.push(line + 'missing guide, element, level or group, row ignored.')
        return
      }
      var option = Number(r.option)
      if (!Number.isFinite(option)) {
        warnings.push(line + 'option "' + r.option + '" is not a number, treated as 1.')
        option = 1
      }
      if (!termsByGroup.has(r.group)) warnings.push(line + 'group "' + r.group + '" has no terms in terms.csv.')
      var level = r.level.toLowerCase()
      if (guides.indexOf(r.guide) < 0) guides.push(r.guide)
      if (levels.indexOf(level) < 0) levels.push(level)
      if (elements.indexOf(r.element) < 0) elements.push(r.element)
      recs.push({ guide: r.guide, element: r.element, level: level, option: option, group: r.group })
    })
    levels.sort(function (a, b) { return rank(LEVEL_ORDER, a) - rank(LEVEL_ORDER, b) })

    if (warnings.length && window.console) warnings.forEach(function (w) { console.warn('[term-explorer]', w) })
    return { termsByGroup: termsByGroup, recs: recs, guides: guides, levels: levels, elements: elements, warnings: warnings }
  }

  function describeTerm (iri) {
    var ns = NAMESPACES.filter(function (n) { return iri.indexOf(n.iri) === 0 })[0]
    var local = iri.replace(/\/+$/, '').split(/[/#]/).pop()
    return { iri: iri, local: local, name: ns ? ns.prefix + ':' + local : local, namespace: ns ? ns.label : '' }
  }

  function rank (order, v) {
    var i = order.indexOf(v)
    return i < 0 ? order.length : i
  }

  // ---------------------------------------------------------------- query

  /*
   * Returns, per element, the "rules" that apply. A rule is one guide + level,
   * with its options (each option = list of groups). Identical rules from
   * different guides are merged so they are shown once.
   */
  function computeRules (data, state) {
    var byKey = new Map()
    data.recs.forEach(function (r) {
      if (!state.guides.has(r.guide)) return
      if (state.level !== 'all' && r.level !== state.level) return
      var key = r.guide + '\u0000' + r.element + '\u0000' + r.level
      if (!byKey.has(key)) byKey.set(key, { guide: r.guide, element: r.element, level: r.level, options: new Map() })
      var opts = byKey.get(key).options
      if (!opts.has(r.option)) opts.set(r.option, [])
      if (opts.get(r.option).indexOf(r.group) < 0) opts.get(r.option).push(r.group)
    })

    var merged = new Map()
    byKey.forEach(function (rule) {
      var options = Array.from(rule.options.keys()).sort(function (a, b) { return a - b }).map(function (n) {
        return { number: n, groups: rule.options.get(n).slice().sort() }
      })
      var signature = rule.element + '\u0000' + rule.level + '\u0000' + JSON.stringify(options)
      if (!merged.has(signature)) {
        merged.set(signature, { element: rule.element, level: rule.level, guides: [], options: options })
      }
      merged.get(signature).guides.push(rule.guide)
    })

    var byElement = new Map()
    data.elements.forEach(function (e) { byElement.set(e, []) })
    merged.forEach(function (rule) {
      rule.guides.sort(function (a, b) { return data.guides.indexOf(a) - data.guides.indexOf(b) })
      rule.alternatives = rule.options.length - 1
      if (!state.alternatives) rule.options = rule.options.slice(0, 1)
      rule.options.forEach(function (o) {
        o.terms = []
        o.groups.forEach(function (g) {
          (data.termsByGroup.get(g) || []).forEach(function (t) {
            if (o.terms.indexOf(t) < 0) o.terms.push(t)
          })
        })
      })
      byElement.get(rule.element).push(rule)
    })
    byElement.forEach(function (rules) {
      rules.sort(function (a, b) {
        return rank(data.levels, a.level) - rank(data.levels, b.level) ||
          data.guides.indexOf(a.guides[0]) - data.guides.indexOf(b.guides[0])
      })
    })
    return byElement
  }

  /* Flatten rules into unique terms, each with the guide/level/option reasons it is listed. */
  function flattenTerms (rules, data) {
    var byIri = new Map()
    rules.forEach(function (rule) {
      rule.options.forEach(function (opt) {
        opt.terms.forEach(function (t) {
          if (!byIri.has(t.iri)) byIri.set(t.iri, { term: t, reasons: [] })
          rule.guides.forEach(function (g) {
            byIri.get(t.iri).reasons.push({ guide: g, level: rule.level, option: opt.number, group: t.group })
          })
        })
      })
    })
    return Array.from(byIri.values()).sort(function (a, b) {
      return bestLevel(a, data) - bestLevel(b, data) ||
        rank(['required'], a.term.requirement) - rank(['required'], b.term.requirement)
    })
  }

  function bestLevel (item, data) {
    return Math.min.apply(null, item.reasons.map(function (r) { return rank(data.levels, r.level) }))
  }

  function matches (term, q) {
    return !q || term.name.toLowerCase().indexOf(q) >= 0 || term.iri.toLowerCase().indexOf(q) >= 0
  }

  // ---------------------------------------------------------------- UI

  function Explorer (root, data) {
    this.root = root
    this.data = data
    this.state = this.readState()
  }

  Explorer.prototype.readState = function () {
    var p = new URLSearchParams(window.location.search)
    var data = this.data
    var guides = p.getAll('guide').filter(function (g) { return data.guides.indexOf(g) >= 0 })
    var level = p.get('level')
    return {
      guides: new Set(guides.length ? guides : data.guides.slice(0, 1)),
      level: level === 'all' || data.levels.indexOf(level) >= 0 ? level : (data.levels[0] || 'all'),
      alternatives: p.get('alternatives') === '1',
      q: p.get('q') || '',
    }
  }

  Explorer.prototype.writeState = function () {
    var s = this.state
    var p = new URLSearchParams(window.location.search)
    ;['guide', 'level', 'alternatives', 'q'].forEach(function (k) { p.delete(k) })
    this.data.guides.forEach(function (g) { if (s.guides.has(g)) p.append('guide', g) })
    p.set('level', s.level)
    if (s.alternatives) p.set('alternatives', '1')
    if (s.q) p.set('q', s.q)
    var url = window.location.pathname + '?' + p.toString() + window.location.hash
    try { window.history.replaceState(null, '', url) } catch (e) { /* ignore, e.g. file:// */ }
  }

  Explorer.prototype.start = function () {
    var self = this
    var data = this.data
    var s = this.state
    var uid = 'te-' + Math.random().toString(36).slice(2, 8)

    // Guides
    var guideList = el('div', { className: 'te-guides' })
    data.guides.forEach(function (g, i) {
      var input = el('input', { type: 'checkbox', value: g, checked: s.guides.has(g) })
      input.addEventListener('change', function () {
        if (input.checked) s.guides.add(g); else s.guides.delete(g)
        self.update()
      })
      guideList.appendChild(el('label', { className: 'te-guide ' + guideClass(i) }, [
        input, el('span', { className: 'te-guide-name' }, g),
      ]))
    })
    var guideActions = el('div', { className: 'te-guide-actions' }, [
      button('Select all', 'te-link', function () { data.guides.forEach(function (g) { s.guides.add(g) }); self.syncGuides(); self.update() }),
      button('Clear', 'te-link', function () { s.guides.clear(); self.syncGuides(); self.update() }),
    ])

    // Level (segmented radio group)
    var levelGroup = el('div', { className: 'te-segmented', role: 'radiogroup' })
    data.levels.concat(['all']).forEach(function (lv) {
      var input = el('input', { type: 'radio', name: uid + '-level', value: lv, checked: s.level === lv })
      input.addEventListener('change', function () { s.level = lv; self.update() })
      levelGroup.appendChild(el('label', null, [input, el('span', null, lv === 'all' ? 'All levels' : capitalise(lv))]))
    })

    // Alternatives switch
    var altInput = el('input', { type: 'checkbox', className: 'te-switch-input', checked: s.alternatives })
    altInput.addEventListener('change', function () { s.alternatives = altInput.checked; self.update() })
    this.altInput = altInput

    // Search
    var search = el('input', { type: 'search', id: uid + '-q', placeholder: 'e.g. latitude, eco:, protocol', value: s.q, autocomplete: 'off' })
    search.addEventListener('input', function () { s.q = search.value.trim(); self.update() })

    this.guideList = guideList
    this.summary = el('p', { className: 'te-summary', 'aria-live': 'polite' })
    this.results = el('div', { className: 'te-results' })
    this.copyButton = button('Copy term names', 'te-button', function () { self.copyNames() })
    var actions = el('div', { className: 'te-actions' }, [
      this.copyButton,
      button('Download CSV', 'te-button', function () { self.downloadCSV() }),
    ])

    var children = []
    if (data.warnings.length && ENV !== 'prod') {
      children.push(el('details', { className: 'te-warnings' }, [
        el('summary', null, data.warnings.length + ' data problem(s) found in the CSV files (only shown outside production)'),
        el('ul', null, data.warnings.map(function (w) { return el('li', null, w) })),
      ]))
    }
    children.push(
      el('div', { className: 'te-controls' }, [
        el('fieldset', { className: 'te-field te-field-guides' }, [
          el('legend', null, 'Guide'), guideList, guideActions,
        ]),
        el('fieldset', { className: 'te-field' }, [
          el('legend', null, 'Recommendation level'), levelGroup,
        ]),
        el('div', { className: 'te-field' }, [
          el('label', { className: 'te-switch' }, [
            altInput, el('span', { className: 'te-switch-track', 'aria-hidden': 'true' }),
            el('span', null, [el('strong', null, 'Show alternative options'),
              el('small', null, 'Off: only the preferred (first) option for each information element.')]),
          ]),
        ]),
        el('div', { className: 'te-field' }, [
          el('label', { htmlFor: uid + '-q', className: 'te-label' }, 'Filter terms'), search,
        ]),
      ]),
      el('div', { className: 'te-results-header' }, [this.summary, actions]),
      this.results,
      el('p', { className: 'te-source' }, [
        'Source data: ', el('a', { href: DATA_URL + 'guides.csv' }, 'guides.csv'), ' · ',
        el('a', { href: DATA_URL + 'terms.csv' }, 'terms.csv'),
      ])
    )
    this.root.replaceChildren.apply(this.root, children)
    this.update()
  }

  Explorer.prototype.syncGuides = function () {
    var s = this.state
    this.guideList.querySelectorAll('input').forEach(function (i) { i.checked = s.guides.has(i.value) })
  }

  Explorer.prototype.update = function () {
    var self = this
    var data = this.data
    var s = this.state
    this.writeState()
    this.view = []

    if (!s.guides.size) {
      this.summary.textContent = ''
      this.results.replaceChildren(el('p', { className: 'te-empty' }, 'Select at least one guide to see its terms.'))
      return
    }

    var q = s.q.toLowerCase()
    var multi = s.guides.size > 1
    var byElement = computeRules(data, s)
    var sections = []
    var allTerms = new Map()
    var hiddenAlternatives = 0

    byElement.forEach(function (rules, element) {
      if (!rules.length) return
      var section
      if (s.alternatives) section = self.renderRules(element, rules, q, multi, allTerms)
      else section = self.renderFlat(element, rules, q, multi, allTerms)
      rules.forEach(function (r) { hiddenAlternatives += s.alternatives ? 0 : r.alternatives })
      if (section) sections.push(section)
    })

    // Summary
    var n = allTerms.size
    var parts = [n + ' term' + (n === 1 ? '' : 's') + ' in ' + sections.length + ' information element' + (sections.length === 1 ? '' : 's')]
    if (multi && n) {
      var shared = 0
      allTerms.forEach(function (guides) { if (guides.size === s.guides.size) shared++ })
      if (shared) parts.push(shared + ' asked for by ' + (s.guides.size === 2 ? 'both' : 'all ' + s.guides.size) + ' selected guides')
    }
    this.summary.replaceChildren(document.createTextNode(parts.join(' · ') + '.'))
    if (hiddenAlternatives && n) {
      this.summary.appendChild(document.createTextNode(' '))
      this.summary.appendChild(button(hiddenAlternatives + ' alternative option' + (hiddenAlternatives === 1 ? '' : 's') + ' hidden — show', 'te-link', function () {
        self.altInput.checked = true
        s.alternatives = true
        self.update()
      }))
    }

    if (!sections.length) {
      this.results.replaceChildren(el('p', { className: 'te-empty' },
        q ? 'No terms match “' + s.q + '”.' : 'The selected guide(s) have no terms at this level.'))
      return
    }
    this.results.replaceChildren.apply(this.results, sections)
  }

  Explorer.prototype.section = function (element, body) {
    return el('section', { className: 'te-element' }, [el('h3', null, capitalise(element))].concat(body))
  }

  /* Default view: one table of unique terms per element. */
  Explorer.prototype.renderFlat = function (element, rules, q, multi, allTerms) {
    var self = this
    var items = flattenTerms(rules, this.data).filter(function (it) { return matches(it.term, q) })
    if (!items.length) return null
    // A second column is only useful when there is more than one guide or level to tell apart.
    var showWhy = multi || this.state.level === 'all'
    var tbody = el('tbody')
    items.forEach(function (it) {
      self.track(it.term, it.reasons, allTerms)
      var row = el('tr', null, el('td', null, self.termCell(it.term)))
      if (showWhy) {
        var chips = el('td', { className: 'te-why' })
        uniqueReasons(it.reasons, multi).forEach(function (r) { chips.appendChild(self.reasonChip(r, multi)) })
        row.appendChild(chips)
      }
      tbody.appendChild(row)
    })
    var table = el('table', { className: 'te-table' }, [
      el('thead', null, el('tr', null, [
        el('th', { scope: 'col' }, 'Term'),
        showWhy ? el('th', { scope: 'col' }, multi ? 'Asked for by' : 'Level') : null,
      ])),
      tbody,
    ])
    return this.section(element, [el('div', { className: 'te-table-wrap' }, table)])
  }

  /* Alternatives view: per rule, option cards side by side. */
  Explorer.prototype.renderRules = function (element, rules, q, multi, allTerms) {
    var self = this
    var blocks = []
    rules.forEach(function (rule) {
      var cards = []
      rule.options.forEach(function (opt, idx) {
        var terms = opt.terms.filter(function (t) { return matches(t, q) })
        if (!terms.length) return
        terms.forEach(function (t) {
          self.track(t, rule.guides.map(function (g) { return { guide: g, level: rule.level, option: opt.number, group: t.group } }), allTerms)
        })
        var title = rule.options.length > 1 ? 'Option ' + opt.number : 'Terms'
        cards.push(el('div', { className: 'te-option' }, [
          el('div', { className: 'te-option-title' }, [title, idx === 0 && rule.options.length > 1 ? el('span', { className: 'te-tag' }, 'preferred') : null]),
          el('ul', null, terms.map(function (t) { return el('li', null, self.termCell(t)) })),
        ]))
      })
      if (!cards.length) return
      var head = el('div', { className: 'te-rule-head' }, [
        el('span', { className: 'te-level te-level-' + slug(rule.level) }, capitalise(rule.level)),
        multi ? el('span', { className: 'te-rule-guides' }, rule.guides.map(function (g) { return self.guideChip(g) })) : null,
        el('span', { className: 'te-rule-hint' }, rule.options.length > 1 ? 'Provide one of these options:' : 'Provide:'),
      ])
      blocks.push(el('div', { className: 'te-rule' }, [head, el('div', { className: 'te-options' }, cards)]))
    })
    return blocks.length ? this.section(element, blocks) : null
  }

  Explorer.prototype.track = function (term, reasons, allTerms) {
    if (!allTerms.has(term.iri)) allTerms.set(term.iri, new Set())
    reasons.forEach(function (r) { allTerms.get(term.iri).add(r.guide) })
    var view = this.view
    reasons.forEach(function (r) { view.push({ term: term, reason: r }) })
  }

  Explorer.prototype.termCell = function (t) {
    var nodes = [el('a', { className: 'te-term', href: t.iri, target: '_blank', rel: 'noopener', title: t.iri }, t.name)]
    if (t.requirement !== 'required') {
      nodes.push(el('span', { className: 'te-tag te-tag-muted', title: 'Part of the set, but not required within it (' + t.requirement + ')' }, 'optional'))
    }
    return el('span', { className: 'te-term-cell' }, nodes)
  }

  Explorer.prototype.guideChip = function (g) {
    return el('span', { className: 'te-chip ' + guideClass(this.data.guides.indexOf(g)), title: g }, g)
  }

  Explorer.prototype.reasonChip = function (r, multi) {
    var level = el('span', { className: 'te-level te-level-' + slug(r.level) }, capitalise(r.level))
    if (!multi) return level
    return el('span', { className: 'te-chip ' + guideClass(this.data.guides.indexOf(r.guide)), title: r.guide + ' · ' + r.level }, [
      r.guide, el('span', { className: 'te-chip-level' }, r.level),
    ])
  }

  Explorer.prototype.uniqueNames = function () {
    var seen = []
    this.view.forEach(function (v) { if (seen.indexOf(v.term.name) < 0) seen.push(v.term.name) })
    return seen
  }

  Explorer.prototype.copyNames = function () {
    var btn = this.copyButton
    var text = this.uniqueNames().join('\n')
    var done = function (msg) {
      btn.textContent = msg
      setTimeout(function () { btn.textContent = 'Copy term names' }, 1800)
    }
    if (!text) return done('Nothing to copy')
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { done('Copied ✓') }, function () { fallbackCopy(text); done('Copied ✓') })
    } else { fallbackCopy(text); done('Copied ✓') }
  }

  Explorer.prototype.downloadCSV = function () {
    var rows = [['element', 'term', 'iri', 'requirement_in_set', 'guide', 'level', 'option', 'set']]
    var seen = new Set()
    this.view.forEach(function (v) {
      var row = [v.term.element, v.term.name, v.term.iri, v.term.requirement, v.reason.guide, v.reason.level, v.reason.option, v.reason.group]
      var key = row.join('\u0000')
      if (!seen.has(key)) { seen.add(key); rows.push(row) }
    })
    var csv = rows.map(function (r) { return r.map(csvCell).join(',') }).join('\r\n') + '\r\n'
    var url = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }))
    var a = el('a', { href: url, download: 'gbif-term-recommendations.csv' })
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(function () { URL.revokeObjectURL(url) }, 1000)
  }

  // ---------------------------------------------------------------- helpers

  function uniqueReasons (reasons, multi) {
    var out = []
    var seen = new Set()
    reasons.forEach(function (r) {
      var key = (multi ? r.guide : '') + '\u0000' + r.level
      if (!seen.has(key)) { seen.add(key); out.push(r) }
    })
    return out
  }

  function el (tag, props, children) {
    var node = document.createElement(tag)
    if (props) {
      Object.keys(props).forEach(function (k) {
        var v = props[k]
        if (v === undefined || v === null || v === false) return
        if (k in node && k !== 'role' && k.indexOf('aria-') !== 0) node[k] = v
        else node.setAttribute(k, v === true ? '' : v)
      })
    }
    ;[].concat(children === undefined ? [] : children).forEach(function (c) {
      if (c === null || c === undefined || c === false) return
      node.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c)
    })
    return node
  }

  function button (label, className, onClick) {
    var b = el('button', { type: 'button', className: className }, label)
    b.addEventListener('click', onClick)
    return b
  }

  function guideClass (i) { return 'te-g' + (i % GUIDE_COLOURS) }
  function capitalise (s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s }
  function slug (s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-') }
  function csvCell (v) {
    v = String(v === undefined || v === null ? '' : v)
    return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v
  }

  function fallbackCopy (text) {
    var ta = el('textarea', { value: text })
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy') } catch (e) { /* ignore */ }
    ta.remove()
  }
})()

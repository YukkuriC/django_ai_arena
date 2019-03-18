
class TableHolder {
    constructor(id, url, callback = null) {
        this.table = document.getElementById(id)
        this.tbody = this.table.getElementsByTagName('tbody')[0]
        this.panel = document.getElementById(id + '_panel')
        this.page = 0
        this.max_page = -1
        this.base_url = url

        // create DOM
        this.panel.style.display = 'none'
        {
            var classes = 'btn btn-sm btn-info'

            var btn = document.createElement('button')
            btn.innerHTML = '上一页'
            btn.className = classes
            btn.onclick = () => { this.prev_page() }
            this.btn_prev = btn
            this.panel.appendChild(btn)

            btn = document.createElement('span')
            this.page_noticer = btn
            this.panel.appendChild(btn)

            btn = document.createElement('button')
            btn.innerHTML = '下一页'
            btn.className = classes
            btn.onclick = () => { this.next_page() }
            this.btn_next = btn
            this.panel.appendChild(btn)

            btn = document.createElement('button')
            btn.innerHTML = '刷新'
            btn.className = classes
            btn.onclick = () => { this.refresh() }
            this.panel.appendChild(btn)
        }
        this.panel.style.display = ''

        this.refresh(callback)
    }
    refresh(callback = null) {
        var url = this.base_url + '&page=' + this.page
        this.panel.style.display = 'none'
        $.get(url, data => {
            var ind = data.indexOf('|')
            if (ind > 0) {
                this.max_page = data.substr(0, ind)
                this.tbody.innerHTML = data.substr(ind + 1)
            } else {
                this.max_page = 0
            }
            if (this.page <= 0) this.btn_prev.style.display = 'none'
            else this.btn_prev.style.display = ''
            if (this.page >= this.max_page - 1) this.btn_next.style.display = 'none'
            else this.btn_next.style.display = ''
            this.page_noticer.innerHTML = (this.page + 1) + '/' + this.max_page

            this.panel.style.display = ''

            if (callback != null) callback()
        })
    }
    next_page() {
        if (this.max_page <= 0) return
        var new_page = Math.min(this.page + 1, this.max_page - 1)
        if (this.page != new_page) {
            this.page = new_page
            this.refresh()
        }
    }
    prev_page() {
        var new_page = Math.max(this.page - 1, 0)
        if (this.page != new_page) {
            this.page = new_page
            this.refresh()
        }
    }
}
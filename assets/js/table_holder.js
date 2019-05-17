// ajax可翻页表格
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
    parse_cell(trow, table_type, cell_type, content) {
        var cell = document.createElement('td')
        try {
            switch (cell_type) {
                case 'code1':
                case 'code2':
                    if (typeof content[1] == 'number') {
                        var link = document.createElement('a')
                        link.href = '/code/' + content[1]

                        var icon = document.createElement('img')
                        icon.style.display = 'inline-block'
                        icon.src = content[2]
                        link.appendChild(icon)
                        link.innerHTML += content[0]

                        cell.appendChild(link)
                    } else {
                        cell.innerHTML = content[0]
                    }
                    break
                case 'type':
                    cell.innerHTML = content[0]
                    break
                case 'author':
                    var link = document.createElement('a')
                    link.href = '/user/' + content[1]

                    var icon = document.createElement('img')
                    icon.style.display = 'inline-block'
                    icon.src = content[2]
                    link.appendChild(icon)
                    link.innerHTML += content[0]

                    cell.appendChild(link)
                    break
                case 'tools':// button + href
                    content.forEach(btn_content => {
                        var btn = document.createElement('a')
                        btn.className = 'btn-sm btn-info'
                        btn.innerHTML = btn_content[0]
                        btn.href = btn_content[1]
                        cell.appendChild(btn)
                    })
                    break
                default:
                    cell.innerHTML = content
                    break
            }
        }
        catch (e) {
            console.log([trow, table_type, cell_type, content])
        }
        trow.appendChild(cell)
    }
    parse_rows(tbody, data) {
        if (data.status == 0) {
            tbody.innerHTML = ''
            data.rows.forEach(row => {
                var trow = document.createElement('tr')
                trow.onmouseover = Function("this.style.background='rgba(15,155,255,0.2)'")
                trow.onmouseout = Function("this.style.background=''")
                trow.onclick = function () { location.href = data.root + row[0] }
                for (var i = 1; i < row.length; i++) {
                    this.parse_cell(trow, data.type, data.headers[i - 1], row[i])
                }
                tbody.appendChild(trow)
            })
        } else {
            tbody.innerHTML = data.content
        }
    }
    refresh(callback = null) {
        var url = this.base_url + '&page=' + this.page
        this.panel.style.display = 'none'
        $.get(url, data => {
            this.max_page = data.size || 0
            this.parse_rows(this.tbody, data)
            if (this.page <= 0) this.btn_prev.style.display = 'none'
            else this.btn_prev.style.display = ''
            if (this.page >= this.max_page - 1) this.btn_next.style.display = 'none'
            else this.btn_next.style.display = ''
            this.page_noticer.innerHTML = (this.page + 1) + '/' + this.max_page

            this.panel.style.display = ''

            if (callback != null) callback()
        }, 'json')
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
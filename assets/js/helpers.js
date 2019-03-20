// 刷新消息推送区域
function update_messages() {
    $('#message_block').load('/msg/')
}

// randrange
function randrange(x) {
    return Math.floor(Math.random() * x)
}
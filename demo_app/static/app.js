const userInput = document.querySelector('#user-id');
const orderSelect = document.querySelector('#order-id');
const summary = document.querySelector('#order-summary');
const result = document.querySelector('#result');
let orders = [];

function renderOrder() {
  const order = orders.find(item => item.id === orderSelect.value);
  if (order) summary.textContent = `实付 ${order.paid_amount} 分｜已退 ${order.refunded_amount} 分｜${order.status}`;
}

async function loadOrders() {
  const response = await fetch(`/api/orders?user_id=${encodeURIComponent(userInput.value)}`);
  const data = await response.json();
  orders = data.orders;
  orderSelect.replaceChildren();
  for (const order of orders) {
    const option = document.createElement('option');
    option.value = order.id;
    option.textContent = order.id;
    orderSelect.append(option);
  }
  renderOrder();
}

orderSelect.addEventListener('change', renderOrder);
userInput.addEventListener('change', loadOrders);
document.querySelector('#refund-button').addEventListener('click', async () => {
  result.textContent = '提交中…';
  const response = await fetch(`/api/orders/${orderSelect.value}/refund`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_id: userInput.value,
      amount: Number(document.querySelector('#amount').value),
      idempotency_key: document.querySelector('#idempotency-key').value,
    }),
  });
  const data = await response.json();
  if (response.ok) {
    result.textContent = `退款成功：${data.refund_id}，金额 ${data.amount} 分`;
    result.dataset.outcome = 'success';
  } else {
    result.textContent = `退款被拒绝：${data.error}`;
    result.dataset.outcome = 'rejected';
  }
  await loadOrders();
});

loadOrders().catch(error => { result.textContent = `加载失败：${error}`; });

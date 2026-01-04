{% extends "base.html" %}
{% block content %}

<div class="d-flex justify-content-between align-items-center mb-3">
  <h2 class="m-0">📌 Saldos</h2>
  <a class="btn btn-secondary btn-sm" href="/dashboard">⬅ Volver</a>
</div>

<div class="row g-3 mb-3">
  <div class="col-md-4">
    <div class="card p-3">
      <div class="text-muted">Total prestado</div>
      <div class="fs-4 fw-bold">$ {{ "{:,.0f}".format(totales.prestado|float).replace(",", ".") }}</div>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card p-3">
      <div class="text-muted">Total pagado</div>
      <div class="fs-4 fw-bold">$ {{ "{:,.0f}".format(totales.pagado|float).replace(",", ".") }}</div>
    </div>
  </div>
  <div class="col-md-4">
    <div class="card p-3">
      <div class="text-muted">Saldo total</div>
      <div class="fs-4 fw-bold">$ {{ "{:,.0f}".format(totales.saldo|float).replace(",", ".") }}</div>
    </div>
  </div>
</div>

<div class="card p-3">
  <div class="table-responsive">
    <table class="table table-bordered bg-white m-0">
      <thead>
        <tr>
          <th>Cliente</th>
          <th>Cédula</th>
          <th>Teléfono</th>
          <th>Monto</th>
          <th>Pagado</th>
          <th>Saldo</th>
          <th>Último pago</th>
          <th>Tipo</th>
          <th style="width:140px;">Acción</th>
        </tr>
      </thead>
      <tbody>
        {% if filas|length == 0 %}
          <tr><td colspan="9" class="text-center">No hay clientes</td></tr>
        {% endif %}

        {% for r in filas %}
        <tr>
          <td>{{ r.nombre }}</td>
          <td>{{ r.cedula }}</td>
          <td>{{ r.telefono }}</td>
          <td>$ {{ "{:,.0f}".format(r.monto|float).replace(",", ".") }}</td>
          <td>$ {{ "{:,.0f}".format(r.pagado_total|float).replace(",", ".") }}</td>
          <td><b>$ {{ "{:,.0f}".format(r.saldo|float).replace(",", ".") }}</b></td>
          <td>{{ r.ultimo_pago }}</td>
          <td>{{ r.tipo_cobro }}</td>
          <td>
            <a class="btn btn-sm btn-primary w-100" href="/pagos?cedula={{ r.cedula }}">Ver pagos</a>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

{% endblock %}

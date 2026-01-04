{% extends "base.html" %}
{% block content %}

<div class="d-flex justify-content-between align-items-center mb-3">
  <h2 class="m-0">📈 Reportes</h2>
  <a class="btn btn-secondary btn-sm" href="/dashboard">⬅ Volver</a>
</div>

{% if request.query_params.get("error") %}
  <div class="alert alert-danger">No hay datos para exportar con esos filtros.</div>
{% endif %}

<div class="card p-3 mb-3">
  <form method="get" action="/reportes" class="row g-3 align-items-end">
    <div class="col-md-2">
      <div class="form-check">
        <input class="form-check-input" type="checkbox" value="1" id="hoy" name="hoy" {% if hoy == "1" %}checked{% endif %}>
        <label class="form-check-label" for="hoy">Solo hoy</label>
      </div>
    </div>

    <div class="col-md-3">
      <label class="form-label">Desde</label>
      <input type="date" class="form-control" name="desde" value="{{ desde }}">
    </div>

    <div class="col-md-3">
      <label class="form-label">Hasta</label>
      <input type="date" class="form-control" name="hasta" value="{{ hasta }}">
    </div>

    <div class="col-md-2">
      <label class="form-label">Cédula</label>
      <input class="form-control" name="cedula" placeholder="Filtrar" value="{{ cedula }}">
    </div>

    <div class="col-md-2 d-flex gap-2">
      <button class="btn btn-primary w-100">Aplicar</button>
      <a class="btn btn-outline-secondary w-100" href="/reportes">Limpiar</a>
    </div>
  </form>
</div>

<div class="row g-3 mb-3">
  <div class="col-md-6">
    <div class="card p-3">
      <div class="text-muted">Cantidad de pagos</div>
      <div class="fs-4 fw-bold">{{ cantidad }}</div>
    </div>
  </div>
  <div class="col-md-6">
    <div class="card p-3">
      <div class="text-muted">Total (suma de pagos)</div>
      <div class="fs-4 fw-bold">$ {{ "{:,.0f}".format(total|float).replace(",", ".") }}</div>
    </div>
  </div>
</div>

<div class="d-flex gap-2 mb-3">
  <a class="btn btn-success"
     href="/reportes/exportar?hoy={{ hoy }}&desde={{ desde }}&hasta={{ hasta }}&cedula={{ cedula }}">
    📤 Exportar Excel (con filtros)
  </a>
</div>

<div class="card p-3">
  <div class="table-responsive">
    <table class="table table-bordered bg-white m-0">
      <thead>
        <tr>
          <th>Cliente</th>
          <th>Cédula</th>
          <th>Fecha</th>
          <th>Hora</th>
          <th>Valor</th>
          <th>Tipo</th>
          <th>Registrado por</th>
        </tr>
      </thead>

      <tbody>
        {% if pagos|length == 0 %}
          <tr><td colspan="7" class="text-center">No hay pagos con esos filtros</td></tr>
        {% endif %}

        {% for p in pagos %}
        <tr>
          <td>{{ p["cliente"] }}</td>
          <td>{{ p["cedula"] }}</td>
          <td>{{ p["fecha"] }}</td>
          <td>{{ p.get("hora","") }}</td>
          <td>$ {{ "{:,.0f}".format(p["valor"]|float).replace(",", ".") }}</td>
          <td>{{ p["tipo_cobro"] }}</td>
          <td>{{ p.get("registrado_por","") }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>

{% endblock %}

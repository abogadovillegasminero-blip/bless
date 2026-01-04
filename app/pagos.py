{% extends "base.html" %}
{% block content %}

<h2>Registrar Pago</h2>

<form method="post" action="/pagos/guardar" class="card p-3 mb-4">

  <div class="mb-3">
    <label>Cliente</label>
    <select name="cedula" class="form-control" required>
      <option value="">Seleccione cliente</option>
      {% for c in clientes %}
        <option value="{{ c['cedula'] }}">
          {{ c['nombre'] }} - {{ c['cedula'] }}
        </option>
      {% endfor %}
    </select>
  </div>

  <div class="mb-3">
    <label>Valor</label>
    <input type="number" name="valor" class="form-control" required>
  </div>

  <div class="mb-3">
    <label>Fecha</label>
    <input type="date" name="fecha" class="form-control" required>
  </div>

  <button class="btn btn-success w-100">Guardar Pago</button>
</form>

{% if pagos and pagos|length > 0 %}
  <h4 class="mt-3">Últimos pagos</h4>
  <div class="card p-3">
    <div class="table-responsive">
      <table class="table table-bordered mb-0">
        <thead>
          <tr>
            <th>Cliente</th>
            <th>Cédula</th>
            <th>Fecha</th>
            <th>Valor</th>
            <th>Tipo cobro</th>
          </tr>
        </thead>
        <tbody>
          {% for p in pagos %}
            <tr>
              <td>{{ p['cliente'] }}</td>
              <td>{{ p['cedula'] }}</td>
              <td>{{ p['fecha'] }}</td>
              <td>{{ p['valor'] }}</td>
              <td>{{ p['tipo_cobro'] }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
{% endif %}

{% endblock %}

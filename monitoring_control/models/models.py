# -*- coding: utf-8 -*-

from odoo import models, fields, api
# class modulo(models.Model):
#     _name = 'modulo.modulo'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100

class MonitoringProducts(models.Model):
	_name = "monitoring.products"

	monitoring_id = fields.Many2one("monitoring.control")
	product_id = fields.Many2one("product.product",string="Producto", readonly=True)
	fecha = fields.Datetime(string="Fecha prevista", readonly=True)
	product_uom = fields.Many2one("product.uom", string="Unidad de medida", readonly=True)
	product_qty = fields.Float(string="Cantidad", readonly=True)
		

class MonitoringMotivos(models.Model):
	_name = "monitoring.motivos"

	name = fields.Char(string="Motivo")
		

class MonitoringControl(models.Model):
	_name="monitoring.control"

	@api.one
	def _document_id(self):
		if self.id < 10:
			self.name = 'DOC0'+str(self.id)
		else:
			self.name = 'DOC'+str(self.id)

	state = fields.Selection([('borrador', 'Borrador'),('aceptado', 'Aceptado'),('rechazado', 'Rechazado')],default='borrador', string="Estado")
	name = fields.Char(string="N° de documento", compute=_document_id)
	tipo_reg = fields.Selection((('entrada','Entrada'),('salida','Salida')),string="Tipo de registro")
	hora_llegada = fields.Datetime(string="Fecha y hora de llegada")
	hora_ingreso = fields.Datetime(string="Fecha y hora de ingreso")
	nombre_chofer = fields.Char(string="Nombre del chofer")
	tipo_trans = fields.Selection((('1ton','1 Tonelada'),('3ton','3 Toneladas'),('5ton','5 Toneladas'),('10ton','10 Toneladas'),('torton','Torton'),('48pi','48 Pies'),('53pi','53 Pies'),('full','Full'),('c20','Contenedor 20'),('c40','Contenedor 40'),('c48','Contenedor 48'),('c53','Contenedor 53')),string="Tipo de transporte")
	placas_tractor = fields.Char(string="Placas del tractor")
	placas_caja = fields.Char(string="Placas de la caja")
	placas_caja_dos = fields.Char(string="Placas de la caja 2")
	#proveedor_linea = fields.Char(string="Proveedor y linea de transporte")
	tipo_licencia = fields.Selection((('autom','Automovilista'),('chofer','Chofer'),('federal','Federal')), string="Tipo de licencia")
	licencia = fields.Char(string="N° de licencia")
	origen = fields.Char(string="Origen")
	destino = fields.Char(string="Destino")
	cedis = fields.Char(string="Cedis")
	purchase_id = fields.Many2one('purchase.order', string="Orden de compra")
	sale_id = fields.Many2one('sale.order', string="Orden de venta")
	provider_id = fields.Many2one('res.partner', string="Proveedor", related="purchase_id.partner_id", readonly=True)
	carrier_id = fields.Many2one('res.partner', string="Transportista")
	product_lines = fields.One2many("monitoring.products", "monitoring_id", string="Productos", readonly=True)

	motivo_rechazo = fields.Many2one("monitoring.motivos", string="Motivo de rechazo")

	clean_unit = fields.Boolean(string='Unidad limpia', default=False)
	no_leaks = fields.Boolean(string='Sin filtraciones de luz o agua', default=False)
	damage_door_floor = fields.Boolean(string='Daños en pisos o puertas', default=False)
	odor_free = fields.Boolean(string='Libre de olores', default=False)
	no_graffiti = fields.Boolean(string='No graffiti', default=False)
	transport_observations = fields.Text(string='Observaciones del transporte')
	condiciones_trans = fields.Text(string="Condiciones del transporte")

	@api.onchange('purchase_id')
	def onchange_purchase_id(self):
		self.carrier_id = ''
		self.nombre_chofer = ''
		self.tipo_licencia = ''
		self.licencia = ''
		self.origen = ''
		self.destino = ''
		self.cedis = ''
		self.clean_unit = False
		self.no_leaks = False
		self.damage_door_floor = False
		self.odor_free = False
		self.no_graffiti = False
		self.product_lines = []
		lista = []
		if self.purchase_id:
			for p in self.purchase_id.order_line:
				lista.append((0, 4, {'product_id': p.product_id.id, 'fecha': p.date_planned, 'product_uom': p.product_uom.id, 'product_qty': p.product_qty}))
			self.product_lines = lista

	@api.onchange('sale_id')
	def onchange_sale_id(self):
		self.carrier_id = ''
		self.nombre_chofer = ''
		self.tipo_licencia = ''
		self.licencia = ''
		self.origen = ''
		self.destino = ''
		self.cedis = ''
		self.clean_unit = False
		self.no_leaks = False
		self.damage_door_floor = False
		self.odor_free = False
		self.no_graffiti = False
		self.product_lines = []
		lista = []
		fecha = self.sale_id.deadline
		if self.sale_id:
			self.carrier_id = self.sale_id.carrier_line
			self.nombre_chofer = self.sale_id.operator_name
			self.tipo_licencia = self.sale_id.license_type
			self.licencia = self.sale_id.license_number
			self.origen = self.sale_id.route.origin
			self.destino = self.sale_id.route.destination
			self.clean_unit = self.sale_id.clean_unit
			self.no_leaks = self.sale_id.no_leaks
			self.damage_door_floor = self.sale_id.damage_door_floor
			self.odor_free = self.sale_id.odor_free
			self.no_graffiti = self.sale_id.no_graffiti
			for p in self.sale_id.order_line:
				lista.append((0, 4, {'product_id': p.product_id.id, 'fecha': fecha, 'product_uom': p.product_uom.id, 'product_qty': p.product_uom_qty}))
			self.product_lines = lista


	@api.onchange('tipo_reg')
	def onchange_tipo_reg(self):
		if self.tipo_reg == 'salida':
			self.purchase_id = ''

		if self.tipo_reg == 'entrada':
			self.sale_id = ''

	def action_acept_control(self):
		self.ensure_one()
		if self.state == 'borrador':
			self.state = 'aceptado'

	def action_refuse_control(self):
		self.ensure_one()
		if self.state == 'borrador':
			self.state = 'rechazado'

	def action_draft_control(self):
		self.ensure_one()
		if self.state == 'aceptado' or self.state == 'rechazado':
			self.state = 'borrador'

#class StockPickingType(models.Model):
#	_name="stock.picking.type"
#	_inherit="stock.picking.type"
#
#	monitoring_control =fields.Boolean(string="Control de vigilancia", default=False)
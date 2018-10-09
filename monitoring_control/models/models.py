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

class MonitoringControl(models.Model):
	_name="monitoring.control"

	@api.one
	def _document_id(self):
		if self.id < 10:
			self.name='DOC0'+str(self.id)
		else:
			self.name='DOC'+str(self.id)

	state = fields.Selection([('borrador', 'Borrador'),('confirmada', 'Acceso confirmado')],default='borrador', string="Estado")
	name = fields.Char(string="N° de documento", compute=_document_id)
	tipo_reg = fields.Selection((('entrada','Entrada'),('salida','Salida')),string="Tipo de registro")
	hora_llegada = fields.Datetime(string="Fecha y hora de llegada")
	hora_ingreso = fields.Datetime(string="Fecha y hora de ingreso")
	nombre_chofer = fields.Char(string="Nombre del chofer")
	tipo_trans = fields.Selection((('1ton','1 Tonelada'),('3ton','3 Toneladas'),('5ton','5 Toneladas'),('10ton','10 Toneladas'),('torton','Torton'),('48pi','48 Pies'),('53pi','53 Pies'),('full','Full'),('c20','Contenedor 20'),('c40','Contenedor 40'),('c48','Contenedor 48'),('c53','Contenedor 53')),string="Tipo de transporte")
	placas_tractor = fields.Char(string="Placas del tractor")
	placas_caja = fields.Char(string="Placas de la caja")
	placas_caja_dos = fields.Char(string="Placas de la caja 2")
	condiciones_trans = fields.Text(string="Condiciones del transporte")
	proveedor_linea = fields.Char(string="Proveedor y linea de transporte")
	tipo_licencia = fields.Selection((('autom','Automovilista'),('chofer','Chofer'),('federal','Federal')), string="Tipo de licencia")
	licencia = fields.Char(string="N° de licencia")
	origen = fields.Char(string="Origen")
	destino = fields.Char(string="Destino")
	cedis = fields.Char(string="Cedis")
	purchase_id = fields.Many2one('purchase.order', string="Orden de compra")
	#purchase_lines = fields.One2many('purchase.order.line', related="purchase_id.order_line")

	@api.onchange('tipo_reg')
	def onchange_tipo_reg(self):
		if self.tipo_reg=='salida':
			self.purchase_id=''

	def action_confirm_control(self):
		self.ensure_one()
		if self.state == 'borrador':
			self.state = 'confirmada'

	def action_draft_control(self):
		self.ensure_one()
		if self.state == 'confirmada':
			self.state = 'borrador'

#class StockPickingType(models.Model):
#	_name="stock.picking.type"
#	_inherit="stock.picking.type"
#
#	monitoring_control =fields.Boolean(string="Control de vigilancia", default=False)
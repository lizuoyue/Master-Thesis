import numpy as np
import math, random
import os, io, sys, glob
import time, zipfile, paramiko
from PIL import Image, ImageDraw, ImageFilter
if os.path.exists('../Python-Lib/'):
	sys.path.insert(1, '../Python-Lib')

""" Remarks:
	ImageDraw: 0-based indexing, (col_idx, row_idx) if taking image as matrix
"""

BLUR = 0.75
TILE_SIZE = 256

ANCHOR_SCALE   = [16, 32, 64, 128]
ANCHOR_RATIO   = [1.0 / 3, 1.0 / 2, 1, 2, 3]
FEATURE_SHAPE  = [[64, 64], [32, 32], [16, 16], [8, 8]]
FEATURE_STRIDE = [4, 8, 16, 32]

# ANCHOR_SCALE   = [40, 80, 160, 320]
# ANCHOR_RATIO   = [0.5, 1, 2]
# FEATURE_SHAPE  = [[160, 160], [80, 80], [40, 40], [20, 20]]
# FEATURE_STRIDE = [4, 8, 16, 32]

def plotPolygon(img_size = (224, 224), resolution = (28, 28), num_vertices = 6):
	# Set image parameters
	num_row = img_size[1]
	num_col = img_size[0]
	half_x = math.floor(num_col / 2)
	half_y = math.floor(num_row / 2)
	dec_rate = (img_size[0] / resolution[0], img_size[1] / resolution[1])

	# Set polygon parameters
	epsilon = 1.0 / num_vertices
	center_r = math.floor(min(num_row, num_col) * 0.05) # <- Decide polygon's center
	polygon_size = math.floor(min(num_row, num_col) * 0.35) # <- Decide polygon's size
	delta_angle = np.pi * 2 * epsilon
	angle = np.random.uniform(0.0, delta_angle) # <- Decide polygon's first vertex

	# Determin the center of polygon
	center_x = half_x + np.random.randint(-center_r, center_r)
	center_y = half_y + np.random.randint(-center_r, center_r)

	# Determin the polygon vertices
	polygon = []
	polygon_s = []
	for i in range(num_vertices):
		r = polygon_size * np.random.uniform(0.8, 1.1) # <- Decide polygon's size range
		px = math.floor(center_x + r * np.cos(angle))
		py = math.floor(center_y - r * np.sin(angle)) # <- Decide polygon's order (counterclockwise)
		polygon.append((px, py))
		polygon_s.append((math.floor(px / dec_rate[0]), math.floor(py / dec_rate[1])))
		angle += delta_angle * np.random.uniform(1 - epsilon, 1 + epsilon) # <- Decide polygon's vertices
	first_idx = random.choice([i for i in range(num_vertices)])
	polygon = polygon[first_idx:] + polygon[:first_idx]
	polygon_s = polygon_s[first_idx:] + polygon_s[:first_idx]

	# Draw polygon
	color = (0, 204, 255)
	org = Image.new('RGB', img_size, color = (255, 255, 255))
	draw = ImageDraw.Draw(org)
	draw.polygon(polygon, fill = color, outline = color)

	# Add noise to the orginal image
	noise = np.random.normal(0, 40, (num_row, num_col, 3))
	background = np.array(org)
	img = background + noise
	img = np.array((img - np.amin(img)) / (np.amax(img) - np.amin(img)) * 255.0, dtype = np.uint8)
	img = np.array(img / 255.0)
	# Image.fromarray(np.array(img * 255.0, dtype = np.uint8)).show()
	# time.sleep(0.25)

	# Draw boundary
	boundary = Image.new('P', resolution, color = 0)
	draw = ImageDraw.Draw(boundary)
	draw.polygon(polygon_s, fill = 0, outline = 255)
	boundary = np.array(boundary) / 255.0
	# Image.fromarray(np.array(boundary * 255.0, dtype = np.uint8)).show()
	# time.sleep(0.25)

	# Draw vertices
	vertices = Image.new('P', resolution, color = 0)
	draw = ImageDraw.Draw(vertices)
	draw.point(polygon_s, fill = 255)
	vertices = np.array(vertices) / 255.0
	# Image.fromarray(np.array(vertices * 255.0, dtype = np.uint8)).show()
	# time.sleep(0.25)

	# Draw each vertex
	vertex_list = []
	for i in range(num_vertices):
		vertex = Image.new('P', resolution, color = 0)
		draw = ImageDraw.Draw(vertex)
		draw.point([polygon_s[i]], fill = 255)
		vertex = np.array(vertex) / 255.0
		vertex_list.append(vertex)
		# Image.fromarray(np.array(vertex * 255.0, dtype = np.uint8)).show()
		# time.sleep(0.25)
	# vertex_list = np.array(vertex_list)

	# Return
	return img, boundary, vertices, vertex_list






def lurd2xywh(lurd):
	return (
		math.floor((lurd[0] + lurd[2]) / 2),
		math.floor((lurd[1] + lurd[3]) / 2),
		math.fabs(lurd[2] - lurd[0]),
		math.fabs(lurd[3] - lurd[1]),
	)

def xywh2lurd(xywh):
	return (
		math.floor(xywh[0] - xywh[2] / 2),
		math.floor(xywh[1] - xywh[3] / 2),
		math.floor(xywh[0] + xywh[2] / 2),
		math.floor(xywh[1] + xywh[3] / 2),
	)

def plotEllipse(anchor_list, img_size = (640, 640), num_ellipse = 6):
	# Set image parameters
	max_x = img_size[0]
	max_y = img_size[1]
	half_x = math.floor(max_x / 2)
	half_y = math.floor(max_y / 2)
	img_size_s = (math.floor(img_size[0] / 16), math.floor(img_size[1] / 16))

	# Set parameters
	epsilon = 1.0 / num_ellipse
	center_rx = math.floor(max_x * 0.05) # <- Decide the track's center
	center_ry = math.floor(max_y * 0.05)
	track_size_x = math.floor(max_x * 0.35) # <- Decide the track's size
	track_size_y = math.floor(max_y * 0.35)
	delta_angle = np.pi * 2 * epsilon
	angle = np.random.uniform(0.0, delta_angle) # <- Decide the track's first ellipsoid

	# Determin the center of the track
	center_x = half_x + np.random.randint(-center_rx, center_rx)
	center_y = half_y + np.random.randint(-center_ry, center_ry)

	# Draw ellipse
	org = Image.new('RGB', img_size, color = (255, 255, 255))
	draw = ImageDraw.Draw(org)
	bboxes = []
	for i in range(num_ellipse):
		color = tuple(np.random.randint(200, size = 3))
		tx = track_size_x * np.random.uniform(0.8, 1.2) # <- Decide ellipse's size range
		ty = track_size_y * np.random.uniform(0.8, 1.2)
		px = math.floor(center_x + tx * np.cos(angle))
		py = math.floor(center_y - ty * np.sin(angle))
		rx = np.random.randint(math.floor(max_x * 0.08), math.floor(max_x * 0.12))
		ry = np.random.randint(math.floor(rx * 0.7), math.floor(rx * 1.3))
		draw.ellipse((px - rx, py - ry, px + rx, py + ry), fill = color)
		angle += delta_angle * np.random.uniform(1 - epsilon, 1 + epsilon)
		l, u = (max(px - rx, 0), max(py - ry, 0))
		r, d = (min(px + rx, max_x), min(py + ry, max_y))
		# draw.polygon([lu, (rd[0], lu[1]), rd, (lu[0], rd[1])], outline = (0, 255, 0))
		# bboxes.append(list(lurd2xywh(lu + rd)))
		bboxes.append([u, l, d, r])

	if len(bboxes) == 0:
		bboxes = np.zeros((0, 4), np.int32)
	else:
		bboxes = np.array(bboxes)

	num_anchors = anchor_list.shape[0]
	anchor_cls = np.zeros([num_anchors, 2], np.int32)
	rpn_match, anchor_box = buildRPNTargets(anchor_list, bboxes)
	anchor_cls[rpn_match == 1, 0] = 1
	anchor_cls[rpn_match == -1, 1] = 1

	# num_anchors = img_size_s[0] * img_size_s[1] * len(anchor_list)
	# anchor_cls = np.zeros([num_anchors, 2], np.int32)
	# anchor_box = np.zeros([num_anchors, 4], np.float32)
	# pos_anchor = []
	# neg_anchor = []
	# shape = []
	# idx = -1
	# for i in range(img_size_s[1]):
	# 	for j in range(img_size_s[0]):
	# 		x = j * 16 + 8
	# 		y = i * 16 + 8
	# 		for k, (w, h) in enumerate(anchor_list):
	# 			idx += 1
	# 			l, u, r, d = xywh2lurd((x, y, w, h))
	# 			shape.append((l, u, r, d))
	# 			if l >= 0 and u >= 0 and r < img_size[0] and d < img_size[1]:
	# 				box_idx = findBestBox(bboxes, (x, y, w, h))
	# 				if box_idx is not None:
	# 					if box_idx >= 0:
	# 						pos_anchor.append(idx)
	# 						box = bboxes[box_idx]
	# 						anchor_box[idx, 0] = (box[0] - x) / w
	# 						anchor_box[idx, 1] = (box[1] - y) / h
	# 						anchor_box[idx, 2] = math.log(box[2] / w)
	# 						anchor_box[idx, 3] = math.log(box[3] / h)
	# 					else:
	# 						neg_anchor.append(idx)

	# # Random select
	# if len(pos_anchor) > 0:
	# 	pos = np.random.choice(len(pos_anchor), min(128, len(pos_anchor)), replace = False)
	# 	anchor_cls[np.array(pos_anchor)[pos], 0] = 1
	# if len(neg_anchor) > 0:
	# 	neg = np.random.choice(len(neg_anchor), 256 - len(pos_anchor), replace = False)
	# 	anchor_cls[np.array(neg_anchor)[neg], 1] = 1

	# Visualization
	# draw = ImageDraw.Draw(img)
	# for x, y, w, h in bboxes:
	# 	l, u, r, d = xywh2lurd((x, y, w, h))
	# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
	# for idx in list(neg):
	# 	l, u, r, d = shape[neg_anchor[idx]]
	# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
	# for idx in list(pos):
	# 	l, u, r, d = shape[pos_anchor[idx]]
	# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (0, 255, 0))
	# img.show()

	# Add noise to the orginal image
	noise = np.random.normal(0, 40, (max_y, max_x, 3))
	background = np.array(org)
	img = background + noise
	img = np.array((img - np.amin(img)) / (np.amax(img) - np.amin(img)) * 255.0, dtype = np.uint8)
	# img = Image.fromarray(img)#.show() ##############
	img = np.array(img) / 255.0

	# idx = anchor_cls[:, 0] == 1
	# gt_anchor = anchor_list[idx, :]
	# gt = applyBoxesDeltas(gt_anchor, anchor_box[idx, :])
	# draw = ImageDraw.Draw(img)
	# for u, l, d, r in bboxes:
	# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], fill = (0, 0, 255), outline = (0, 0, 255))
	# for i in range(gt.shape[0]):
	# 	u, l, d, r = tuple(gt[i])
	# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (0, 255, 0))
	# 	u, l, d, r = tuple(gt_anchor[i])
	# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
	# img.show()

	return img, anchor_cls, anchor_box

def lonLatToWorld(lon, lat):
	# Truncating to 0.9999 effectively limits latitude to 89.189. This is
	# about a third of a tile past the edge of the world tile.
	siny = math.sin(float(lat) * math.pi / 180.0);
	siny = min(max(siny, -0.9999), 0.9999)
	return \
		TILE_SIZE * (0.5 + float(lon) / 360.0), \
		TILE_SIZE * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) \

def lonLatToPixel(lon, lat, z):
	scale = 2 ** z
	wx, wy = lonLatToWorld(lon, lat)
	return math.floor(wx * scale), math.floor(wy * scale)

def lonLatToTile(lon, lat, z):
	scale = 2 ** z
	wx, wy = lonLatToWorld(lon, lat)
	return math.floor(wx * scale / TILE_SIZE), math.floor(wy * scale / TILE_SIZE)

def pixelToLonLat(px, py, z):
	# Return the longitude of the left boundary of a pixel
	# and the latitude of the upper boundary of a pixel
	scale = 2 ** z
	lon = (float(px) / float(scale) / TILE_SIZE - 0.5) * 360.0
	temp = math.exp((0.5 - float(py) / float(scale) / TILE_SIZE) * 4 * math.pi)
	lat = math.asin((temp - 1.0) / (temp + 1.0)) / math.pi * 180.0
	return lon, lat

def norm(array):
	ma = np.amax(array)
	mi = np.amin(array)
	if ma == mi:
		return np.zeros(array.shape)
	else:
		return (array - mi) / (ma - mi)

def rotate(img_size, lurd):
	l, u, r, d = lurd
	return (img_size[1], img_size[0]), (u, img_size[0] - r, d, img_size[0] - l)

class BoundingBox(object):
	# size: (width, height)
	def __init__(self, lon, lat, zoom, scale, size = (224, 224)):
		self.center_lon = lon
		self.center_lat = lat
		self.size = size
		self.z = zoom + scale - 1
		self.center_px, self.center_py = lonLatToPixel(lon, lat, self.z)
		self.left, self.up = pixelToLonLat(
			self.center_px - math.floor(size[0] / 2), \
			self.center_py - math.floor(size[1] / 2), \
			self.z \
		)
		self.right, self.down = pixelToLonLat(
			self.center_px + math.floor(size[0] / 2), \
			self.center_py + math.floor(size[1] / 2), \
			self.z \
		)

	def lonLatToRelativePixel(self, lon, lat):
		# 0-based
		px, py = lonLatToPixel(lon, lat, self.z)
		return math.floor(px - self.center_px + self.size[0] / 2), math.floor(py - self.center_py + self.size[1] / 2)




class DataGenerator(object):
	# num_col, num_row
	def __init__(self, fake, data_path = None, max_seq_len = None, img_size = (224, 224), resolution = None):
		if fake:
			self.fake = True
			assert(max_seq_len != None)
			self.max_seq_len = max_seq_len
			self.img_size = img_size
			self.resolution = resolution
			self.blank = np.zeros(resolution, dtype = np.float32)
		else:
			# 
			self.fake = False
			assert(max_seq_len != None)
			self.max_seq_len = max_seq_len
			self.img_size = img_size
			self.resolution = resolution
			assert(data_path.endswith('.zip'))

			# 
			self.data_path = data_path.lstrip('./').replace('.zip', '')
			self.archive = zipfile.ZipFile(data_path, 'r')
			self.building_id_set = set()
			for filename in self.archive.namelist():
				if filename.startswith('__MACOSX'):
					continue
				parts = filename.split('/')
				if len(parts) == 3:
					self.building_id_set.add(int(parts[1]))
			print('Totally %d buildings.' % len(self.building_id_set))
			
			# 
			self.good_building_id_set = set()
			self.bad_building_id_set = set()
			for bid in self.building_id_set:
				self.dispatchBuilding(bid)
			print('Totally %d good buildings.' % len(self.good_building_id_set))
			print('Totally %d bad buildings.' % len(self.bad_building_id_set))

			#
			train_prob = 0.95
			self.good_building_id_list = list(self.good_building_id_set)
			self.good_building_id_list.sort()
			random.seed(0)
			random.shuffle(self.good_building_id_list)
			random.seed()
			split = int(train_prob * len(self.good_building_id_list))
			self.id_list_train = self.good_building_id_list[:split]
			self.id_list_valid = self.good_building_id_list[split:]
			self.bad_id_list = list(self.bad_building_id_set)

			# 
			self.blank = np.zeros(resolution, dtype = np.uint8)
			self.vertex_pool = [[] for i in range(resolution[1])]
			for i in range(resolution[1]):
				for j in range(resolution[0]):
					self.vertex_pool[i].append(np.copy(self.blank))
					self.vertex_pool[i][j][i, j] = 255
					self.vertex_pool[i][j] = Image.fromarray(self.vertex_pool[i][j])
			return

	def dispatchBuilding(self, building_id, th = 0.9):
		# Set path
		building_id = str(building_id)
		path = self.data_path + '/' + building_id

		#
		lines = self.archive.read(path + '/shift.txt').decode('utf-8').split('\n')
		edge_prob, _ = lines[1].strip().split()
		edge_prob = float(edge_prob)

		#
		if edge_prob >= th:
			self.good_building_id_set.add(int(building_id))
		else:
			self.bad_building_id_set.add(int(building_id))
		return

	def blur(self, img):
		# img: PIL.Image object
		if BLUR is not None:
			img = img.convert('L').filter(ImageFilter.GaussianBlur(BLUR))
			img = np.array(img, np.float32)
			img = np.minimum(img * (1.2 / np.max(img)), 1.0)
			# Image.fromarray(np.array(img * 255.0, dtype = np.uint8)).show()
		else:
			img = np.array(img, np.float32) / 255.0
		return img

	def showImagePolygon(self, img, polygon, rotate):
		mask = Image.new('RGBA', img.size, color = (255, 255, 255, 0))
		draw = ImageDraw.Draw(mask)
		draw.polygon(polygon, fill = (255, 0, 0, 128), outline = (255, 0, 0, 128))
		merge = Image.alpha_composite(img, mask.rotate(rotate))
		merge.show()
		return

	def distL1(self, p1, p2):
		return math.fabs(p1[0] - p2[0]) + math.fabs(p1[1] - p2[1])

	def getSingleData(self, building_id):
		# Set path
		building_id = str(building_id)
		path = self.data_path + '/' + building_id

		# Rotate
		rotate = random.choice([0, 90, 180, 270])

		# Get image, polygon coordinates and shift
		img = Image.open(io.BytesIO(self.archive.read(path + '/img.png')))
		lines = self.archive.read(path + '/polygon.txt').decode('utf-8').split('\n')
		polygon = []
		for line in lines:
			if line.strip() != '':
				x, y = line.strip().split()
				polygon.append((int(x), int(y)))
		lines = self.archive.read(path + '/shift.txt').decode('utf-8').split('\n')
		shift_i, shift_j = lines[0].strip().split()
		shift_i, shift_j = int(shift_i), int(shift_j)
		polygon = [(x + shift_j, y + shift_i) for x, y in polygon]

		# Get local small patch
		pad_rate = random.random() * 0.1 + 0.1
		min_x, max_x = img.size[0], 0
		min_y, max_y = img.size[1], 0
		for x, y in polygon:
			min_x = min(x, min_x)
			min_y = min(y, min_y)
			max_x = max(x, max_x)
			max_y = max(y, max_y)
		min_x = max(min_x - math.floor(img.size[0] * pad_rate), 0)
		min_y = max(min_y - math.floor(img.size[1] * pad_rate), 0)
		max_x = min(max_x + math.floor(img.size[0] * pad_rate), img.size[0])
		max_y = min(max_y + math.floor(img.size[1] * pad_rate), img.size[1])

		# Adjust image and polygon
		img_patch = img.crop((min_x, min_y, max_x, max_y))
		patch_info = [img_patch.size[0], img_patch.size[1], rotate]
		img_patch = img_patch.resize(self.img_size, resample = Image.BICUBIC).rotate(rotate)
		# img_patch.show()
		# time.sleep(0.25)
		# img_patch_backup = img_patch
		img_patch = np.array(img_patch)[..., 0: 3] / 255.0
		x_rate = self.img_size[0] / (max_x - min_x)
		y_rate = self.img_size[1] / (max_y - min_y)
		res_x = self.resolution[0] / self.img_size[0]
		res_y = self.resolution[1] / self.img_size[1]

		polygon_patch = []
		for x, y in polygon:
			a = math.floor((x - min_x) * x_rate * res_x)
			b = math.floor((y - min_y) * y_rate * res_y)
			if not polygon_patch or self.distL1((a, b), polygon_patch[-1]) > 0:
				polygon_patch.append((a, b))

		start = random.randint(0, len(polygon_patch) - 1)
		polygon_patch = polygon_patch[start:] + polygon_patch[:start]
		# self.showImagePolygon(img_patch_backup, [(x * 4, y * 4) for x, y in polygon_patch], rotate)
		# time.sleep(0.25)

		# Draw boundary and vertices
		boundary = Image.new('P', (self.resolution[0], self.resolution[1]), color = 0)
		draw = ImageDraw.Draw(boundary)
		draw.polygon(polygon_patch, fill = 0, outline = 255)
		boundary = self.blur(boundary.rotate(rotate))
		# time.sleep(0.25)

		vertices = Image.new('P', (self.resolution[0], self.resolution[1]), color = 0)
		draw = ImageDraw.Draw(vertices)
		draw.point(polygon_patch, fill = 255)
		vertices = self.blur(vertices.rotate(rotate))
		# time.sleep(0.25)

		# Get each single vertex
		vertex_input = []
		vertex_output = []
		for i, (x, y) in enumerate(polygon_patch):
			# self.vertex_pool[int(y)][int(x)].rotate(rotate).show()
			# time.sleep(0.25)
			v = self.vertex_pool[int(y)][int(x)].rotate(rotate)
			vertex_input.append(np.array(v, dtype = np.float32) / 255.0)
			if i == 0:
				continue
			# vertex_output.append(self.blur(v))
			vertex_output.append(np.array(v, dtype = np.float32) / 255.0)
		assert(len(vertex_output) == len(vertex_input) - 1)

		# 
		while len(vertex_input) < self.max_seq_len:
			vertex_input.append(np.array(self.blank, dtype = np.float32))
		while len(vertex_output) < self.max_seq_len:
			vertex_output.append(np.array(self.blank, dtype = np.float32))
		vertex_input = np.array(vertex_input)
		vertex_output = np.array(vertex_output)

		# Get end signal
		seq_len = len(polygon_patch)
		end = [0.0 for i in range(self.max_seq_len)]
		end[seq_len - 1] = 1.0
		# seq_len = 6
		# end ? ? ? ? ? ! ? ? ? ?
		# out 1 2 3 4 5 ? ? ? ? ?
		#  in 0 1 2 3 4 5 ? ? ? ?
		end = np.array(end)

		# Return
		return img_patch, boundary, vertices, vertex_input, vertex_output, end, seq_len, patch_info

	def getDataBatch(self, batch_size, mode = None):
		# Fake
		if self.fake:
			return self.getFakeDataBatch(batch_size)

		# Real
		res = []
		if mode == 'train':
			sel = np.random.choice(len(self.id_list_train), batch_size, replace = True)
			for i in sel:
				res.append(self.getSingleData(self.id_list_train[i]))
		if mode == 'valid':
			sel = np.random.choice(len(self.id_list_valid), batch_size, replace = True)
			for i in sel:
				res.append(self.getSingleData(self.id_list_valid[i]))
		if mode == 'test':
			sel = np.random.choice(len(self.bad_id_list), batch_size, replace = True)
			for i in sel:
				res.append(self.getSingleData(self.bad_id_list[i]))
		return (np.array([item[i] for item in res]) for i in range(8))

	def getFakeDataBatch(self, batch_size):
		res = []
		num_v = np.random.choice(6, batch_size, replace = True) + 4
		for seq_len in num_v:
			img, boundary, vertices, vertex_input = plotPolygon(
				img_size = self.img_size,
				resolution = self.resolution,
				num_vertices = seq_len
			)
			while len(vertex_input) < self.max_seq_len:
				vertex_input.append(np.copy(self.blank))
			vertex_output = vertex_input[1:] + [self.blank]
			vertex_input = np.array(vertex_input)
			vertex_output = np.array(vertex_output)
			end = [0.0 for i in range(self.max_seq_len)]
			end[seq_len - 1] = 1.0
			end = np.array(end)
			res.append((img, boundary, vertices, vertex_input, vertex_output, end, seq_len, [224, 224, 0]))
		return (np.array([item[i] for item in res]) for i in range(8))

class AnchorGenerator(object):
	# num_col, num_row
	def __init__(self, fake, data_path, from_server):
		if fake:
			self.fake = True
		else:
			self.fake = False
			self.from_server = from_server
			# 
			if from_server:
				self.ssh = paramiko.SSHClient()
				self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
				self.ssh.connect('cab-e81-28.ethz.ch', username = 'zoli', password = '64206960lzyLZY')
				self.sftp = self.ssh.open_sftp()

			with open('./AreaIdxList.txt', 'r') as f:
				self.area_idx_list = eval(f.read())
			print('Totally %d areas.' % len(self.area_idx_list))
			random.shuffle(self.area_idx_list)

			#
			train_prob = 0.95
			split = int(train_prob * len(self.area_idx_list))
			self.idx_list_train = self.area_idx_list[:split]
			self.idx_list_valid = self.area_idx_list[split:]

			self.data_path = data_path

		self.anchors = generatePyramidAnchors(ANCHOR_SCALE, ANCHOR_RATIO, FEATURE_SHAPE, FEATURE_STRIDE, 1)
		return

	def getDataBatch(self, batch_size, mode = None):
		# Fake
		if self.fake:
			return self.getFakeDataBatch(batch_size)

		# Real
		idx = []
		res = []
		if mode == 'train':
			sel = np.random.choice(len(self.idx_list_train), batch_size, replace = True)
			for i in sel:
				res.append(self.getSingleData(self.idx_list_train[i]))
				idx.append(self.idx_list_train[i])
		if mode == 'valid':
			sel = np.random.choice(len(self.idx_list_valid), batch_size, replace = True)
			for i in sel:
				res.append(self.getSingleData(self.idx_list_valid[i]))
				idx.append(self.idx_list_valid[i])
		return idx, (np.array([item[i] for item in res]) for i in range(3))

	def getSingleData(self, area_idx):
		# Set path
		path = self.data_path + '/' + area_idx

		# Rotate
		n_rotate = 0 # random.choice([0, 1, 2, 3])

		# 
		if self.from_server:
			while True:
				try:
					img = Image.open(io.BytesIO(self.sftp.open(path + '/img.png').read())).resize((256, 256), resample = Image.BICUBIC)
					lines = self.sftp.open(path + '/polygons.txt').read().decode('utf-8').split('\n')
					break
				except:
					print('Try again.')
		else:
			img = Image.open(path + '/img.png').resize((256, 256), resample = Image.BICUBIC)
			f = open(path + '/polygons.txt', 'r')
			lines = f.readlines()
			f.close()

		org_size = img.size
		img = img.rotate(n_rotate * 90)
		img_size = img.size
		img_size_s = (math.floor(img_size[0] / 16), math.floor(img_size[1] / 16))
		num_anchors = self.anchors.shape[0]

		org = np.array(img)[..., 0: 3] / 255.0

		polygons = []
		for line in lines:
			if line.strip() != '':
				if line.strip() == '%':
					polygons.append([])
				else:
					x, y = line.strip().split()
					polygons[-1].append((int(x), int(y)))

		gt_boxes = []
		pad = 0
		for polygon in polygons:
			w, h = (640, 640)
			p = np.array(polygon, np.int32)
			l = max(0, p[:, 0].min())
			u = max(0, p[:, 1].min())
			r = min(w, p[:, 0].max())
			d = min(h, p[:, 1].max())
			if r > l and d > u:
				for _ in range(n_rotate):
					(w, h), (l, u, r, d) = rotate((w, h), (l, u, r, d))
				gt_boxes.append([u - pad, l - pad, d + pad, r + pad])
		if len(gt_boxes) == 0:
			gt_boxes = np.zeros((0, 4), np.int32)
		else:
			gt_boxes = np.array(gt_boxes)

		anchor_cls = np.zeros([num_anchors, 2], np.int32)
		rpn_match, anchor_box = buildRPNTargets(self.anchors * 2.5, gt_boxes)
		anchor_cls[rpn_match == 1, 0] = 1
		anchor_cls[rpn_match == -1, 1] = 1

		# anchor_box = np.zeros([num_anchors, 4], np.float32)
		# pos_anchor = []
		# neg_anchor = []
		# shape = []
		# idx = -1
		# for i in range(img_size_s[1]):
		# 	for j in range(img_size_s[0]):
		# 		x = j * 16 + 8
		# 		y = i * 16 + 8
		# 		for k, (w, h) in enumerate(self.anchor_list):
		# 			idx += 1
		# 			l, u, r, d = xywh2lurd((x, y, w, h))
		# 			shape.append((l, u, r, d))
		# 			if l >= 0 and u >= 0 and r < img_size[0] and d < img_size[1]:
		# 				box_idx = findBestBox(bboxes, (x, y, w, h))
		# 				if box_idx is not None:
		# 					if box_idx >= 0:
		# 						pos_anchor.append(idx)
		# 						box = bboxes[box_idx]
		# 						anchor_box[idx, 0] = (box[0] - x) / w
		# 						anchor_box[idx, 1] = (box[1] - y) / h
		# 						anchor_box[idx, 2] = math.log(box[2] / w)
		# 						anchor_box[idx, 3] = math.log(box[3] / h)
		# 					else:
		# 						neg_anchor.append(idx)

		# # Random select
		# if len(pos_anchor) > 0:
		# 	pos = np.random.choice(len(pos_anchor), min(128, len(pos_anchor)), replace = False)
		# 	anchor_cls[np.array(pos_anchor)[pos], 0] = 1
		# if len(neg_anchor) > 0:
		# 	neg = np.random.choice(len(neg_anchor), 256 - len(pos_anchor), replace = False)
		# 	anchor_cls[np.array(neg_anchor)[neg], 1] = 1

		# Visualization
		# draw = ImageDraw.Draw(img)
		# for x, y, w, h in bboxes:
		# 	l, u, r, d = xywh2lurd((x, y, w, h))
		# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
		# for idx in list(neg):
		# 	l, u, r, d = shape[neg_anchor[idx]]
		# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
		# for idx in list(pos):
		# 	l, u, r, d = shape[pos_anchor[idx]]
		# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (0, 255, 0))
		# img.show()

		# idx = anchor_cls[:, 0] == 1
		# gt_anchor = self.anchors[idx, :]
		# gt = applyBoxesDeltas(gt_anchor, anchor_box[idx, :])
		# draw = ImageDraw.Draw(img)
		# for u, l, d, r in gt_boxes:
		# 	u, l, d, r = u / 2.5, l / 2.5, d / 2.5, r / 2.5
		# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], fill = (0, 0, 255), outline = (0, 0, 255))
		# for i in range(gt.shape[0]):
		# 	u, l, d, r = tuple(gt[i])
		# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (0, 255, 0))
		# 	u, l, d, r = tuple(gt_anchor[i])
		# 	draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
		# img.show()

		return org, anchor_cls, anchor_box

	def getFakeDataBatch(self, batch_size):
		res = []
		num_e = np.random.choice(4, batch_size, replace = True) + 2
		for num in num_e:
			res.append(plotEllipse(anchor_list = self.anchors, num_ellipse = num, img_size = (256, 256)))
		return (np.array([item[i] for item in res]) for i in range(3))

	# def recover(self, path, img, obj_logit, bbox_info):
	# 	for idx in range(obj_logit.shape[0]):
	# 		li = []
	# 		for i in range(obj_logit.shape[2]):
	# 			for j in range(obj_logit.shape[1]):
	# 				x = i * 16 + 8
	# 				y = j * 16 + 8
	# 				for k, (w, h) in enumerate(self.anchor_list):
	# 					l, u, r, d = xywh2lurd((x, y, w, h))
	# 					if l < 0 or u < 0 or r > img.shape[2] or d > img.shape[1]:
	# 						pass
	# 					else:
	# 						prob = obj_logit[idx, j, i, k]
	# 						prob = 1 / (1 + math.exp(prob[1] - prob[0]))
	# 						li.append((prob, (j, i, k), (x, y, w, h)))
	# 		li.sort()
	# 		boxes = []
	# 		for item in li[-300: ]:
	# 			j, i, k = item[1]
	# 			x, y, w, h = item[2]
	# 			box_info = bbox_info[idx, j, i, k]
	# 			box = [None, None, None, None]
	# 			box[0] = math.floor(box_info[0] * w + x)
	# 			box[1] = math.floor(box_info[1] * h + y)
	# 			box[2] = math.floor(math.exp(box_info[2]) * w)
	# 			box[3] = math.floor(math.exp(box_info[3]) * h)
	# 			boxes.append(list(xywh2lurd(tuple(box))))
	# 		boxes = np.array(boxes)
	# 		org = Image.fromarray(np.array(img[idx] * 255.0, dtype = np.uint8))
	# 		draw = ImageDraw.Draw(org)
	# 		for i in range(boxes.shape[0]):
	# 			l, u, r, d = tuple(list(boxes[i, :]))
	# 			draw.polygon([(l, u), (r, u), (r, d), (l, d)], outline = (255, 0, 0))
	# 		org.save(path + '/%d.png' % idx)



class AreaGenerator(object):
	def __init__(self, data_path):
		self.data_path = data_path
		self.info = {}
		for item in glob.glob(data_path + '/*.txt'):
			with open(item, 'r') as f:
				boxes = [line.strip().split() for line in f.readlines()]
				boxes = [[int(item) for item in line] for line in boxes]
			idx = item.replace(data_path + '/', '').replace('.txt', '')
			self.info[idx] = boxes
		self.idx_list = list(self.info.keys())
		self.idx_list.sort()
		self.pad = 0.3
		self.i = 0
		self.end = False

	def getData(self):
		img = Image.open('../Chicago_Area/%s/img.png' % self.idx_list[self.i])
		img = np.array(img)
		patches = []
		org_info = []
		for u, l, d, r in self.info[self.idx_list[self.i]]:
			y1, x1, y2, x2 = u*2.5, l*2.5, d*2.5, r*2.5
			h, w = y2 - y1, x2 - x1
			y1, x1, y2, x2 = int(max(0, y1 - h * self.pad)), int(max(0, x1 - w * self.pad)), int(min(640, y2 + h * self.pad)), int(min(640, x2 + w * self.pad))
			if y1 < y2 and x1 < x2:
				patches.append(np.array(Image.fromarray(img[y1: y2, x1: x2, 0: 3]).resize((224, 224), resample = Image.BICUBIC))/255.0)
				org_info.append([y1, x1, y2, x2])
		num = len(patches)
		for i in range(40 - num):
			patches.append(np.zeros((224, 224, 3), dtype=np.float32))
		self.i += 1
		self.end = self.i == len(self.idx_list)
		return img, np.array(patches), org_info


if __name__ == '__main__':
	# ag = AnchorGenerator(fake = False, data_path = '/local/lizuoyue/Chicago_Area', from_server = True)
	# ag.getDataBatch(8, mode = 'train')
	# print(ag.anchors)
	a = AreaGenerator('./res')
	a.getData()



import argparse
import math
import re
import time
from collections import defaultdict
import numpy as np
import itertools
import json
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
import random
import sys
import matplotlib.pyplot as plt

# -------------------------------------------------------------------
# Вспомогательные функции
# -------------------------------------------------------------------
def format_time(seconds: float) -> str:
	hours = int(seconds // 3600)
	minutes = int((seconds % 3600) // 60)
	secs = seconds % 60
	parts = []
	if hours > 0:
		parts.append(f"{hours} ч")
	if minutes > 0:
		parts.append(f"{minutes} мин")
	if secs > 0 or not parts:
		parts.append(f"{secs:.2f} сек")
	return " ".join(parts)

def round_param(p, tolerance=0.003):
	nearest_int = round(p)
	if abs(p - nearest_int) < tolerance:
		return float(nearest_int)
	return p

def penalty(var):
	if -0.003 < var < 0.003:
		return abs(var) * 333.33
	elif 0.997 < abs(var) < 1.003:
		return abs(abs(var) - 1) * 333.33 + 1
	else:
		return 2.0

def format_float(val):
	s = f"{val:.6f}".rstrip('0').rstrip('.')
	return s if s.startswith('-') else s

def extract_singular_t_values(formula_str):
	points = set()
	pattern = r'abs\(t([+-]\d+(?:\.\d+)?)?\)'
	matches = re.findall(pattern, formula_str)
	for num_str in matches:
		if num_str == '':
			points.add(0.0)
		elif num_str.startswith('+'):
			points.add(-float(num_str[1:]))
		elif num_str.startswith('-'):
			points.add(float(num_str[1:]))
		else:
			points.add(float(num_str))
	return points

def parse_t_values_from_comment(line):
	if 't values:' not in line:
		return set()
	after = line.split('t values:')[-1].strip()
	if not after:
		return set()
	points = set()
	for token in after.split():
		try:
			points.add(float(token))
		except ValueError:
			continue
	return points

def compute_confidence_factor(t, all_points):
	if not all_points:
		return 1.0
	s_list = sorted(all_points)
	min_s = s_list[0]
	max_s = s_list[-1]
	if min_s <= t <= max_s:
		d_min = min(abs(t - s) for s in all_points)
		max_gap = 0.0
		for i in range(len(s_list) - 1):
			gap = s_list[i+1] - s_list[i]
			if gap > max_gap:
				max_gap = gap
		if max_gap == 0.0:
			return 3.0
		half_gap = max_gap / 2.0
		factor = 3.0 - (d_min / half_gap)
		return factor
	else:
		if t < min_s:
			d = min_s - t
		else:
			d = t - max_s
		L = 0.558
		factor = 1.0 + 2.0 * math.exp(-d / L)
		return factor

def preprocess_formula(formula_str):
	s = formula_str.strip()
	if s.startswith('x(t) ='):
		s = s[len('x(t) ='):].strip()
	elif s.startswith('y(t) ='):
		s = s[len('y(t) ='):].strip()
	if '=' in s and s.index('=') < 10:
		s = s.split('=', 1)[1].strip()
	s = s.replace('²', '^2').replace('³', '^3').replace('⁴', '^4')
	s = s.replace('⁵', '^5').replace('⁶', '^6').replace('⁷', '^7')
	s = s.replace('⁸', '^8').replace('⁹', '^9').replace('⁰', '^0')
	s = s.replace('⁻', '^-').replace('⁺', '^+')
	s = s.replace('^', '**')
	return s

def safe_eval(expr, t_val):
	namespace = {
		't': t_val,
		'abs': abs,
		'cos': math.cos,
		'sqrt': math.sqrt,
		'__builtins__': None,
	}
	return eval(expr, namespace)

def predict_with_formula(formula_str, t):
	singular_ts = extract_singular_t_values(formula_str)
	tol = 1e-9
	t_shifted = t
	for ts in singular_ts:
		if abs(t - ts) < tol:
			t_shifted = ts + 1e-12
			break
	expr = preprocess_formula(formula_str)
	return safe_eval(expr, t_shifted)

def read_models(filename):
	with open(filename, 'r', encoding='utf-8') as f:
		lines = f.readlines()
	models = []
	current_var = None
	current_seed = None
	current_formula_lines = []
	current_r2 = None
	current_data_ts = set()
	i = 0
	while i < len(lines):
		line = lines[i].strip()
		if not line:
			i += 1
			continue
		if line.startswith('#') and '(' in line and 'seed=' in line:
			if current_formula_lines and current_r2 is not None:
				formula = ' '.join(current_formula_lines)
				models.append({
					'var': current_var,
					'seed': current_seed,
					'formula': formula,
					'r2': current_r2,
					'singular_ts': extract_singular_t_values(formula),
					'data_ts': current_data_ts
				})
				current_formula_lines = []
				current_r2 = None
				current_data_ts = set()
			if 't values:' in line:
				before_tv, _ = line.split('t values:', 1)
				current_data_ts = parse_t_values_from_comment(line)
				parts = before_tv.strip().split('(')
				var_part = parts[0].replace('#', '').strip()
				current_var = var_part
				seed_part = parts[1].replace(')', '').strip()
				if seed_part.startswith('seed='):
					current_seed = int(seed_part.split('=')[1])
				else:
					current_seed = None
			else:
				current_data_ts = set()
				parts = line.split('(')
				var_part = parts[0].replace('#', '').strip()
				current_var = var_part
				seed_part = parts[1].replace(')', '').strip()
				if seed_part.startswith('seed='):
					current_seed = int(seed_part.split('=')[1])
				else:
					current_seed = None
			i += 1
			continue
		if re.match(r'[a-zA-Z]\(t\)\s*=', line):
			if current_formula_lines:
				current_formula_lines = []
			current_formula_lines.append(line)
			i += 1
			continue
		if line.startswith('coefR'):
			parts = line.split('=')
			if len(parts) == 2:
				try:
					current_r2 = float(parts[1].strip())
				except ValueError:
					current_r2 = 0.0
			i += 1
			continue
		if current_formula_lines:
			current_formula_lines.append(line)
		i += 1
	if current_formula_lines and current_r2 is not None:
		formula = ' '.join(current_formula_lines)
		models.append({
			'var': current_var,
			'seed': current_seed,
			'formula': formula,
			'r2': current_r2,
			'singular_ts': extract_singular_t_values(formula),
			'data_ts': current_data_ts
		})
	return models

def process_variable(models, var_name, t):
	if not models:
		return None
	print(f"\n--- Переменная {var_name}(t) ---")
	predictions = []
	r2_list = []
	all_points = set()
	for i, model in enumerate(models, 1):
		formula = model['formula']
		r2 = model['r2']
		all_points.update(model['singular_ts'])
		all_points.update(model['data_ts'])
		try:
			val = predict_with_formula(formula, t)
			predictions.append(val)
			r2_list.append(r2)
			rel_error_percent = (1.0 - r2) * 100.0
			print(f"{i}: {var_name} = {val:.6f} ± {rel_error_percent:.2f}%")
		except Exception as e:
			print(f"Ошибка при вычислении модели {i}: {e}")
			predictions.append(None)
			r2_list.append(None)
	valid_indices = [i for i, p in enumerate(predictions) if p is not None]
	if not valid_indices:
		return None
	valid_preds = [predictions[i] for i in valid_indices]
	valid_r2 = [r2_list[i] for i in valid_indices]
	intervals = []
	for w, r2 in zip(valid_preds, valid_r2):
		delta = abs(w) * (1.0 - r2)
		intervals.append((w - delta, w + delta))
	global_lower = min(iv[0] for iv in intervals)
	global_upper = max(iv[1] for iv in intervals)
	factor = compute_confidence_factor(t, all_points)
	if factor != 1.0:
		center = (global_lower + global_upper) / 2.0
		half_width = (global_upper - global_lower) / 2.0
		new_half = half_width / factor
		new_lower = center - new_half
		new_upper = center + new_half
		return (new_lower, new_upper)
	else:
		return (global_lower, global_upper)

# -------------------------------------------------------------------
# Класс IDWPolyModel – теперь принимает все данные через конструктор
# -------------------------------------------------------------------
class IDWPolyModel:
	def __init__(self, target_name, W_all, bounds, max_iters, seed,
				 X_all, input_names, train_idx, test_idx, support_idx,
				 X_train_global, X_test_global, X_support_global):
		self.target_name = target_name
		self.W_all = W_all
		self.W_train = W_all[train_idx]
		self.W_test  = W_all[test_idx]
		self.W_support = W_all[support_idx]
		self.bounds = bounds
		self.max_iters = max_iters
		self.seed = seed

		# Сохраняем данные, которые раньше были глобальными
		self.X_all = X_all
		self.input_names = input_names
		self.train_idx = train_idx
		self.test_idx = test_idx
		self.support_idx = support_idx
		self.X_train_global = X_train_global
		self.X_test_global = X_test_global
		self.X_support_global = X_support_global

		self.poly_feat = PolynomialFeatures(degree=2, include_bias=True)
		self.poly_feat.fit(self.X_all)
		self.feature_names = self.poly_feat.get_feature_names_out(input_features=self.input_names)

		XP_train_full = self.poly_feat.transform(self.X_train_global)
		self.initial_poly_coef = np.linalg.lstsq(XP_train_full, self.W_train, rcond=None)[0]

		self.best_params = None
		self.final_poly_coef = None
		self.train_rmse = None
		self.test_rmse = None
		self.r2 = None
		self.loss = None

	def poly_val(self, coef, X):
		XP = self.poly_feat.transform(X)
		return XP @ coef

	def idw_correction(self, X_query, X_train, R_train, a, b, lam, amp):
		diff = X_query[:, None, :] - X_train[None, :, :]
		abs_diff = np.abs(diff)
		inner = np.sum(abs_diff ** a, axis=2)
		inner[inner < 1e-12] = 1e-12
		D = inner ** b
		dist_eucl = np.sqrt(np.sum(diff**2, axis=2))
		C = (np.cos(dist_eucl + lam) + 1.0) * amp
		Phi = C / D
		num = np.sum(R_train[None, :] * Phi, axis=1)
		den = np.sum(Phi, axis=1)
		den[den == 0] = 1.0
		return num / den

	def get_poly_coef(self, a, b, lam, amp, adaptive=False):
		a_round = round_param(a)
		b_round = round_param(b)
		lam_round = round_param(lam)
		amp_round = round_param(amp)
		if not adaptive:
			return self.initial_poly_coef.copy()
		else:
			baseline_coef = self.initial_poly_coef.copy()
			R_train_full = self.W_train - self.poly_val(baseline_coef, self.X_train_global)
			W_corrected = self.W_support - self.idw_correction(
				self.X_support_global, self.X_train_global, R_train_full,
				a_round, b_round, lam_round, amp_round
			)
			XP_support = self.poly_feat.transform(self.X_support_global)
			poly_coef = np.linalg.lstsq(XP_support, W_corrected, rcond=None)[0]
			return poly_coef

	def predict(self, X_query, a, b, lam, amp, adaptive):
		a_round = round_param(a)
		b_round = round_param(b)
		lam_round = round_param(lam)
		amp_round = round_param(amp)
		if not adaptive:
			poly_coef = self.initial_poly_coef
		else:
			poly_coef = self.get_poly_coef(a, b, lam, amp, adaptive)
		base = self.poly_val(poly_coef, X_query)
		if adaptive and abs(amp_round) > 1e-12:
			R_train_full = self.W_train - self.poly_val(poly_coef, self.X_train_global)
			corr = self.idw_correction(X_query, self.X_train_global, R_train_full,
									   a_round, b_round, lam_round, amp_round)
			return base + corr
		else:
			return base

	def total_loss(self, params, step=None):
		a, b, lam, amp = params
		d = len(params)
		M_adapt = 3 ** d
		adaptive = (step is not None and step >= M_adapt)
		a_round = round_param(a)
		b_round = round_param(b)
		lam_round = round_param(lam)
		amp_round = round_param(amp)
		preds = self.predict(self.X_test_global, a_round, b_round, lam_round, amp_round, adaptive)
		rmse = np.sqrt(np.mean((preds - self.W_test)**2))
		poly_coef = self.get_poly_coef(a, b, lam, amp, adaptive)
		reg_sum = (penalty(a_round) + penalty(b_round) + penalty(lam_round) + penalty(amp_round) +
				   sum(penalty(c) for c in poly_coef))
		reg_factor = reg_sum + 0.1
		return reg_factor * rmse

	def optimize(self, verbose=True):
		if self.seed is not None:
			random.seed(self.seed)
			np.random.seed(self.seed)

		d = len(self.bounds)
		M = 3 ** d
		param_levels = [(b[0], b[1], (b[0] + b[1]) / 2.0) for b in self.bounds]
		initial_points = list(itertools.product(*param_levels))
		history = []
		for pt in initial_points:
			p = np.array(pt, dtype=float)
			loss = self.total_loss(p, step=0)
			history.append({'params': p, 'loss': loss})

		s = M
		best_idx = np.argmin([h['loss'] for h in history])
		best_params_ever = history[best_idx]['params'].copy()
		last_sum = float('inf')

		while s <= self.max_iters:
			oldest = history[0]
			newest = history[-1]
			L_s = oldest['loss']
			L_sN = newest['loss']
			var_s = oldest['params']
			var_sN = newest['params']
			new_params = var_s.copy()
			for j in range(d):
				low, high = self.bounds[j]
				if L_sN == L_s:
					avg_val = np.mean([h['params'][j] for h in history])
					new_val = avg_val
				else:
					step_val = L_s * (var_sN[j] - var_s[j]) / (L_sN - L_s)
					new_val = var_s[j] - step_val / s
				new_val = np.clip(new_val, low, high)
				new_params[j] = new_val

			is_duplicate = any(np.allclose(new_params, h['params'], rtol=1e-6, atol=1e-6) for h in history)
			if is_duplicate:
				new_params = np.array([np.random.uniform(low, high) for low, high in self.bounds])

			new_loss = self.total_loss(new_params, step=s)

			if new_loss < history[best_idx]['loss']:
				best_params_ever = new_params.copy()
				best_idx = None

			if new_loss <= 1e-12:
				if verbose:
					print("Loss=0")
				break

			future_history = history[1:] + [{'params': new_params, 'loss': new_loss}]
			sum_after = sum(h['loss'] for h in future_history)
			if (s + 1) % M == 0:
				if sum_after > last_sum * 1.001:
					if best_idx is None:
						best_idx = np.argmin([h['loss'] for h in history])
						print("Loss: "+f"{history[best_idx]['loss']}")
						best_params_ever = history[best_idx]['params'].copy()
					break
				else:
					last_sum = sum_after
					print("Loss: "+f"{sum_after/M}")

			history.pop(0)
			history.append({'params': new_params, 'loss': new_loss})
			if best_idx is None:
				best_idx = np.argmin([h['loss'] for h in history])
			s += 1
		else:
			best_idx = np.argmin([h['loss'] for h in history])
			best_params_ever = history[best_idx]['params'].copy()

		self.best_params = best_params_ever
		a, b, lam, amp = best_params_ever
		self.final_poly_coef = self.get_poly_coef(a, b, lam, amp, adaptive=True)
		# Гарантируем, что best_idx — целое число
		if best_idx is None:
			best_idx = np.argmin([h['loss'] for h in history])
		self.loss = history[best_idx]['loss']

		def final_predict(X):
			R_train = self.W_train - self.poly_val(self.final_poly_coef, self.X_train_global)
			return self.poly_val(self.final_poly_coef, X) + self.idw_correction(
				X, self.X_train_global, R_train,
				round_param(a), round_param(b), round_param(lam), round_param(amp)
			)
		self.predict_func = final_predict

		train_preds = final_predict(self.X_train_global)
		test_preds = final_predict(self.X_test_global)
		self.train_rmse = np.sqrt(np.mean((train_preds - self.W_train)**2))
		self.test_rmse = np.sqrt(np.mean((test_preds - self.W_test)**2))
		self.r2 = r2_score(self.W_test, test_preds)
		print("R^2 = "+f"{self.r2}")
		return self.best_params, self.loss
		
	def generate_formula(self):
		a, b, lam, amp = self.best_params
		poly_coef = self.final_poly_coef
		a_round = round_param(a)
		b_round = round_param(b)
		lam_round = round_param(lam)
		amp_round = round_param(amp)

		poly_coef_rounded = np.array([round_param(c) for c in poly_coef])
		poly_terms = []
		for coef, name in zip(poly_coef_rounded, self.feature_names):
			if abs(coef) < 1e-12:
				continue
			if name == '1':
				term = f"{format_float(coef)}"
			elif abs(coef - 1.0) < 1e-9:
				term = f"+{name}"
			elif abs(coef + 1.0) < 1e-9:
				term = f"-{name}"
			else:
				sign = '+' if coef > 0 else '-'
				term = f"{sign}{format_float(abs(coef))}*{name}"
			poly_terms.append(term)
		poly_str = ''.join(poly_terms).lstrip('+')
		if not poly_str:
			poly_str = "0"

		R_train = self.W_train - self.poly_val(poly_coef_rounded, self.X_train_global)

		if abs(amp_round) < 1e-12 or np.max(np.abs(R_train)) < 1e-9:
			arg_str = ', '.join(self.input_names)
			return f"{self.target_name}({arg_str}) = {poly_str}"

		num_terms = []
		den_terms = []
		for i, (xi_vec, ri) in enumerate(zip(self.X_train_global, R_train)):
			if abs(ri) < 1e-12:
				continue
			diff_strs = []
			abs_strs = []
			sq_strs = []
			for j, feat in enumerate(self.input_names):
				xj = xi_vec[j]
				diff = f"{feat}-{format_float(xj)}" if xj >= 0 else f"{feat}+{format_float(abs(xj))}"
				diff_strs.append(diff)
				abs_strs.append(f"abs({diff})")
				sq_strs.append(f"({diff})^2")
			abs_sum = " + ".join([f"{s}^{format_float(a_round)}" for s in abs_strs])
			D = f"({abs_sum})^{format_float(b_round)}"
			sq_sum = " + ".join(sq_strs)
			dist_eucl = f"sqrt({sq_sum})"
			if abs(lam_round) < 1e-12:
				cos_arg = f"{dist_eucl}"
			else:
				cos_arg = f"({dist_eucl} + {format_float(lam_round)})"
			C = f"(cos({cos_arg}) + 1) * {format_float(amp_round)}"
			phi = f"{C} / {D}"
			den_terms.append(phi)
			num_terms.append(f"{format_float(ri)} * {phi}")

		numerator = " + ".join(num_terms).replace("+ -", "- ")
		denominator = " + ".join(den_terms).replace("+ -", "- ")
		arg_str = ', '.join(self.input_names)
		return f"{self.target_name}({arg_str}) = {poly_str} + ({numerator}) / ({denominator})"

# -------------------------------------------------------------------
# Функция learn (обучение)
# -------------------------------------------------------------------
def learn(datafile='data2extra.json', outfile='all_formulas.txt'):
	start = time.perf_counter()

	with open(datafile, 'r', encoding='utf-8') as f:
		data = json.load(f)

	meta_keys = {'need', 'bounds', 'iter'}
	need_str = data.get('need', '')
	if not need_str:
		print("Ошибка: в JSON отсутствует поле 'need' со списком целевых переменных.")
		sys.exit(1)
	target_names = [s.strip() for s in need_str.split(',')]
	print(f"Целевые переменные: {target_names}")

	all_keys = set(data.keys())
	input_names = []
	for key in all_keys:
		if key in meta_keys or key in target_names:
			continue
		if isinstance(data[key], (list, np.ndarray)) and len(data[key]) > 0:
			input_names.append(key)
	input_names.sort()
	print(f"Входные признаки: {input_names}")

	X_all = np.column_stack([data[name] for name in input_names])
	n_samples = X_all.shape[0]
	dim_in = len(input_names)

	if 'bounds' in data:
		bounds = [tuple(b) for b in data['bounds']]
	else:
		bounds = [(0.1, 4.0), (0.1, 4.0), (-0.1, np.pi), (0, 4.0)]
	max_iters = data.get('iter', 500)

	# Разбиение train/test/support
	n_total = len(X_all)
	edge = max(1, n_total // 6)
	mid_start = edge
	mid_end = n_total - edge

	train_idx = []
	test_idx = []
	test_idx.extend(range(0, min(edge, n_total)))
	test_idx.extend(range(max(mid_end, 0), n_total))
	mid_indices = list(range(mid_start, mid_end))
	for i, idx in enumerate(mid_indices):
		if i % 4 == 3:
			test_idx.append(idx)
		else:
			train_idx.append(idx)
	train_idx.sort()
	test_idx.sort()

	part_size_1_12 = max(1, n_total // 12)
	p1_end = part_size_1_12
	p2_start = p1_end
	p2_end = p2_start + part_size_1_12
	p3_start = p2_end
	p3_end = p3_start + (n_total * 2 // 3)
	p4_start = p3_end
	p4_end = p4_start + part_size_1_12
	support_idx = []
	support_idx.extend(range(p2_start, min(p2_end, n_total)))
	support_idx.extend(range(p3_start, min(p3_end, n_total)))
	support_idx.extend(range(p4_start, min(p4_end, n_total)))
	support_idx.sort()

	X_train_global = X_all[train_idx]
	X_test_global  = X_all[test_idx]
	X_support_global = X_all[support_idx]

	print(f"Всего точек: {n_total}")

	output_filename = outfile
	with open(output_filename, "w", encoding="utf-8") as f:
		f.write("")

	models = []
	seeds = [42, 123, int(time.time())]
	all_formulas = {}

	for target in target_names:
		W_all = np.array(data[target])
		all_models_for_target = []
		best_loss = float('inf')
		formulas_for_target = []

		for i, seed in enumerate(seeds):
			print(f"\n--- Запуск {i+1} для {target} ---")
			model = IDWPolyModel(
				target_name=target,
				W_all=W_all,
				bounds=bounds,
				max_iters=max_iters,
				seed=seed,
				X_all=X_all,
				input_names=input_names,
				train_idx=train_idx,
				test_idx=test_idx,
				support_idx=support_idx,
				X_train_global=X_train_global,
				X_test_global=X_test_global,
				X_support_global=X_support_global
			)
			params, loss = model.optimize(verbose=True)
			all_models_for_target.append(model)
			a, b, lam, amp = params

			rounded_coef = np.where(np.abs(model.final_poly_coef) < 1e-12, 0.0, model.final_poly_coef)
			coef_str = "[" + " ".join(f"{c:.6f}".rstrip('0').rstrip('.') if c != 0 else "0" for c in rounded_coef) + "]"

			formula = model.generate_formula()
			formulas_for_target.append((seed, formula, model.r2, a, b, lam, amp))

			with open(output_filename, "a", encoding="utf-8") as f:
				if n_total < 100:
					coefR = (n_total - 1) / 100
				else:
					coefR = 1 - 1 / n_total

				t_idx = None
				for idx, name in enumerate(input_names):
					if name == 't':
						t_idx = idx
						break
				if t_idx is not None:
					unique_t = sorted(set(X_train_global[:, t_idx]))
					t_vals_str = ' '.join(f"{v:.6f}".rstrip('0').rstrip('.') for v in unique_t)
					f.write(f"# {target} (seed={seed}) t values: {t_vals_str}\n")
				else:
					f.write(f"# {target} (seed={seed})\n")

				f.write(formula + "\n")
				f.write(f"coefR = {model.r2 * coefR + coefR:.6f}\n\n")

			if loss < best_loss:
				best_loss = loss
				best_model_for_target = model

		models.append(all_models_for_target)

	diff = time.perf_counter() - start
	print(f"Обучение успешно. Затрачено: {format_time(diff)}")

	# Визуализация (логика не изменена)
	if dim_in == 1:
		x_plot = np.linspace(X_all[:,0].min(), X_all[:,0].max(), 200).reshape(-1,1)
		
		# Для каждой целевой переменной создаём отдельный график
		for var_idx, var_models in enumerate(models):  # var_models – список из 3 моделей для одной переменной
			plt.figure(figsize=(8,5))
			# Рисуем предсказания всех трёх моделей разными цветами/стилями
			for model in var_models:
				y_pred = model.predict_func(x_plot)
				plt.plot(x_plot, y_pred, label=f'seed={model.seed}, R²={model.r2:.3f}')
			# Точки обучающей и тестовой выборки (они одинаковы для всех моделей одной переменной)
			# Берём данные из первой модели, так как W_train и W_test одинаковы для всех seed
			first_model = var_models[0]
			plt.scatter(first_model.X_train_global[:,0], first_model.W_train, 
						c='blue', s=20, label='Train')
			plt.scatter(first_model.X_test_global[:,0], first_model.W_test, 
						c='red', s=20, label='Test')
			plt.xlabel(input_names[0])
			plt.ylabel(first_model.target_name)
			plt.title(f"{first_model.target_name} – все модели")
			plt.legend()
			plt.tight_layout()
			plt.show()
	elif dim_in == 2:
		# Берём только первую модель для каждой переменной (индекс 0)
		first_models = [var_models[0] for var_models in models]
		
		fig = plt.figure(figsize=(6*len(first_models), 5))
		x_min, x_max = X_all[:,0].min(), X_all[:,0].max()
		y_min, y_max = X_all[:,1].min(), X_all[:,1].max()
		margin = 0.1 * max(x_max - x_min, y_max - y_min)
		xx, yy = np.meshgrid(np.linspace(x_min - margin, x_max + margin, 40),
							 np.linspace(y_min - margin, y_max + margin, 40))
		grid_points = np.column_stack((xx.ravel(), yy.ravel()))
		
		for i, model in enumerate(first_models):
			ax = fig.add_subplot(1, len(first_models), i+1, projection='3d')
			zz = model.predict_func(grid_points).reshape(xx.shape)
			ax.plot_surface(xx, yy, zz, alpha=0.6, cmap='viridis', edgecolor='none')
			ax.scatter(model.X_train_global[:,0], model.X_train_global[:,1],
					   model.W_train, c='blue', s=20, label='Train')
			ax.scatter(model.X_test_global[:,0], model.X_test_global[:,1],
					   model.W_test, c='red', s=20, label='Test')
			ax.set_xlabel(input_names[0])
			ax.set_ylabel(input_names[1])
			ax.set_zlabel(model.target_name)
			ax.set_title(f"{model.target_name}\nRMSE={model.test_rmse:.3f}, R²={model.r2:.3f}")
			ax.legend()
		plt.tight_layout()
		plt.show()
	else:
		print(f"Визуализация для размерности входа {dim_in} не поддерживается.")

# -------------------------------------------------------------------
# Функция predict (предсказание) – без изменений
# -------------------------------------------------------------------
def predict(t_val, formula_file='all_formulas.txt'):
	try:
		all_models = read_models(formula_file)
	except FileNotFoundError:
		print(f"Файл '{formula_file}' не найден.")
		return

	if not all_models:
		print("В файле не найдено ни одной модели.")
		return

	models_by_var = defaultdict(list)
	for m in all_models:
		models_by_var[m['var']].append(m)

	for var in list(models_by_var.keys()):
		models_by_var[var] = models_by_var[var][:3]

	t = t_val
	intervals = {}
	for var in models_by_var:
		iv = process_variable(models_by_var[var], var, t)
		if iv is not None:
			intervals[var] = iv

	if not intervals:
		print("Не удалось вычислить ни одного интервала.")
		return

	print()
	for var in sorted(intervals.keys()):
		lo, hi = intervals[var]
		print(f"{var} в интервале: ({lo:.6f}, {hi:.6f})")

# -------------------------------------------------------------------
# Главная функция
# -------------------------------------------------------------------
def main():
	parser = argparse.ArgumentParser(description='Обучение IDW-полиномиальной модели и предсказание.')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('--learn', nargs='?', const='data2extra.json', default=None,
					   help='Запустить обучение (можно указать файл JSON, по умолчанию data2extra.json)')
	group.add_argument('--predict', type=float, metavar='T', help='Предсказать для заданного значения t')
	args = parser.parse_args()
	if args.learn is not None:
		learn(args.learn)
	elif args.predict is not None:
		predict(args.predict)

if __name__ == '__main__':
	main()
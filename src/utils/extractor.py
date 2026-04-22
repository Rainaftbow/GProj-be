from collections import Counter
import hashlib
import math
import os
import re
import pefile
from flask import current_app


def calculate_entropy(data):
    """计算数据香农熵"""
    if not data:
        return 0

    counter = Counter(data)
    entropy = 0
    total = len(data)

    for count in counter.values():
        p = count / total
        entropy -= p * math.log2(p)

    return entropy


class FeatureExtractor:
    """PE文件特征提取器"""

    def __init__(self, file_path, top_50_api_dict=None):
        self.file_path = file_path
        self.file_size = os.path.getsize(file_path)
        self.file_content = self._read_file()
        self.top_50_api_dict = top_50_api_dict or []

    def _read_file(self):
        """读取文件内容"""
        with open(self.file_path, "rb") as f:
            return f.read()

    def calculate_hashes(self):
        """计算文件哈希值"""
        md5 = hashlib.md5(self.file_content).hexdigest()
        sha256 = hashlib.sha256(self.file_content).hexdigest()
        return md5, sha256

    def get_byte_histogram(self):
        """计算字节分布直方图（L1归一化）"""
        histogram = [0] * 256
        total_bytes = len(self.file_content)

        for byte in self.file_content:
            histogram[byte] += 1

        # L1归一化
        normalized = [count / total_bytes for count in histogram]
        return normalized

    def extract_pe_features(self):
        """提取PE文件特征"""
        features = {}

        with pefile.PE(data=self.file_content, fast_load=False) as pe:

            # 文件统计特征
            features["file_size"] = self.file_size
            features["global_entropy"] = calculate_entropy(self.file_content)

            # DOS头MZ签名
            features["e_magic"] = pe.DOS_HEADER.e_magic

            # PE文件头特征
            features["machine"] = pe.FILE_HEADER.Machine
            features["number_of_sections"] = pe.FILE_HEADER.NumberOfSections
            features["time_date_stamp"] = pe.FILE_HEADER.TimeDateStamp

            # PE可选头特征
            features["address_of_entry_point"] = pe.OPTIONAL_HEADER.AddressOfEntryPoint
            features["image_base"] = pe.OPTIONAL_HEADER.ImageBase
            features["section_alignment"] = pe.OPTIONAL_HEADER.SectionAlignment
            features["subsystem"] = pe.OPTIONAL_HEADER.Subsystem

            # 节区特征
            # 检查异常节区名称
            normal_sections = current_app.config.get('FEATURE_CONFIG')["NORMAL_SECTIONS"]
            features["is_abnormal_section_name"] = int(
                any(
                    section.Name.rstrip(b"\x00") not in normal_sections
                    for section in pe.sections
                )
            )

            # 所有节区尺寸压缩比
            # 磁盘总占用 / 内存总占用
            total_raw_size = 0
            total_virtual_size = 0

            for section in pe.sections:
                total_raw_size += section.SizeOfRawData
                total_virtual_size += section.Misc_VirtualSize

            if total_virtual_size > 0:
                features["all_sections_size_ratio"] = total_raw_size / total_virtual_size
            else:
                features["all_sections_size_ratio"] = 1.0

            # wx节区占比
            num_sections = len(pe.sections)
            wx_sections_count = 0

            for section in pe.sections:
                if (section.Characteristics & 0x80000000) and (section.Characteristics & 0x20000000):
                    wx_sections_count += 1

            features["wx_section_ratio"] = wx_sections_count / num_sections if num_sections > 0 else 0

            # 最高信息熵节区
            section_entropies = []
            for section in pe.sections:
                data = section.get_data()
                if data:
                    section_entropies.append(calculate_entropy(data))

            features["max_section_entropy"] = (
                max(section_entropies) if section_entropies else 0
            )

            # 导入表特征并收集 API
            api_list = []
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                features["num_imported_dlls"] = len(pe.DIRECTORY_ENTRY_IMPORT)
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    for imp in entry.imports:
                        if imp.name:
                            api_list.append(
                                imp.name.decode("utf-8", errors="ignore")
                            )
            else:
                features["num_imported_dlls"] = 0

            # 导出表特征
            features["is_export_present"] = int(
                hasattr(pe, "DIRECTORY_ENTRY_EXPORT")
            )

            # 资源信息
            if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
                resource_size = pe.OPTIONAL_HEADER.DATA_DIRECTORY[
                    pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]
                ].Size
                features["resource_size"] = resource_size
            else:
                features["resource_size"] = 0


        # 字符串特征
        pattern = rf"[ -~]{{{current_app.config.get('FEATURE_CONFIG')["NUM_PRINTABLE_STR_LEN"]},}}".encode()
        strings = re.findall(pattern, self.file_content)
        features["num_printable_strings"] = len(strings)

        suspicious_pattern = re.compile(current_app.config.get('FEATURE_CONFIG')["SUSPICIOUS_PATTERNS"])
        features["suspicious_str_count"] = sum(
            1 for s in strings if suspicious_pattern.search(s)
        )

        # 字节直方图
        features["byte_histogram"] = self.get_byte_histogram()

        # API组合特征，2-gram 对齐映射
        api_2gram_feature = [0.0] * 50
        if len(api_list) >= 2 and self.top_50_api_dict:
            file_2grams = [f"{api_list[i]}_{api_list[i + 1]}" for i in range(len(api_list) - 1)]
            total_file_grams = len(file_2grams)
            if total_file_grams > 0:
                file_gram_counts = Counter(file_2grams)
                for idx, target_gram in enumerate(self.top_50_api_dict):
                    api_2gram_feature[idx] = file_gram_counts.get(target_gram, 0) / total_file_grams

        features["top_50_api_2gram"] = api_2gram_feature
        return features

    def extract_all_features(self):
        """提取所有特征并返回为字典"""
        md5, sha256 = self.calculate_hashes()
        features = self.extract_pe_features()
        features["file_md5"] = md5
        features["file_sha256"] = sha256
        return features
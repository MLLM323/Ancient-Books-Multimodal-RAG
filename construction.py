import os
import pandas as pd
import csv

# ==============================================================================
# 步骤 1: 配置和元数据定义 (聚焦于人物基本属性)
# ==============================================================================

# 请务必将此路径修改为您自己的CBDB CSV文件存放目录
BASE_DIR = r"csv_output___2222"

# 定义本次任务所需的核心实体
ENTITY_CONFIG = {
    'Person': {
        'file': 'CBDB_20250520_BIOG_MAIN.csv',
        'id_col': 'c_personid',
        'name_col': 'c_name_chn'
    },
    'AltNameType': {
        'file': 'CBDB_20250520_ALTNAME_CODES.csv',
        'id_col': 'c_name_type_code',
        'name_col': 'c_name_type_desc_chn'
    },
    'Status': {
        'file': 'CBDB_20250520_STATUS_CODES.csv',
        'id_col': 'c_status_code',
        'name_col': 'c_status_desc_chn'
    },
    'Dynasty': {
        'file': 'CBDB_20250520_DYNASTIES.csv',
        'id_col': 'c_dy',
        'name_col': 'c_dynasty_chn'
    },
    'Choronym': {
        'file': 'CBDB_20250520_CHORONYM_CODES.csv',
        'id_col': 'c_choronym_code',
        'name_col': 'c_choronym_chn'
    }
}

# 定义本次要提取的人物基本属性关系
# 注意：有些关系直接在BIOG_MAIN表中，有些在专门的关系表中
RELATIONSHIP_CONFIG = {
    'Person_AltName': {
        'file': 'CBDB_20250520_ALTNAME_DATA.csv',
        'subject': ('Person', 'c_personid'),
        'predicate': ('AltNameType', 'c_alt_name_type_code'),
        'object_is_literal': True, # 宾语是直接的文本，不是ID
        'object_col': 'c_alt_name_chn'
    },
    'Person_Status': {
        'file': 'CBDB_20250520_STATUS_DATA.csv',
        'subject': ('Person', 'c_personid'),
        'predicate': '社会身份为',
        'object': ('Status', 'c_status_code')
    },
    # --- 以下关系直接从 BIOG_MAIN 表中提取 ---
    'Person_Dynasty': {
        'file': 'CBDB_20250520_BIOG_MAIN.csv', # 源文件是 BIOG_MAIN 本身
        'subject': ('Person', 'c_personid'),
        'predicate': '所属朝代为',
        'object': ('Dynasty', 'c_dy')
    },
    'Person_Choronym': {
        'file': 'CBDB_20250520_BIOG_MAIN.csv', # 源文件是 BIOG_MAIN 本身
        'subject': ('Person', 'c_personid'),
        'predicate': '郡望为',
        'object': ('Choronym', 'c_choronym_code')
    }
}

# ==============================================================================
# 步骤 2: 辅助函数和主逻辑 (稍作修改以适应新需求)
# ==============================================================================

def load_lookup_dict(file_path, id_col, name_col):
    """从实体CSV文件加载ID到名称的查找字典"""
    lookup = {}
    try:
        # 优化读取，特别是对于可能包含非数字ID的DYNASTIES表
        df = pd.read_csv(file_path, usecols=[id_col, name_col], dtype={id_col: str}, low_memory=False)
        df.dropna(subset=[id_col, name_col], inplace=True)
        lookup = pd.Series(df[name_col].values, index=df[id_col]).to_dict()
        print(f"成功加载查找字典: {os.path.basename(file_path)} ({len(lookup)} 条目)")
        return lookup
    except Exception as e:
        print(f"错误: 加载 {file_path} 失败 - {e}")
        return {}

def extract_triples(relationship_info, lookups, output_writer):
    """从单个关系表中提取三元组"""
    file_path = os.path.join(BASE_DIR, relationship_info['file'])
    
    subject_entity_name, subject_col = relationship_info['subject']
    subject_lookup = lookups[subject_entity_name]

    # --- 获取谓语 ---
    predicate_info = relationship_info['predicate']
    is_dynamic_predicate = isinstance(predicate_info, tuple)

    # --- 获取宾语 ---
    object_is_literal = relationship_info.get('object_is_literal', False)
    if not object_is_literal:
        object_entity_name, object_col = relationship_info['object']
        object_lookup = lookups[object_entity_name]
    else:
        object_col = relationship_info['object_col']

    # --- 确定需要读取的列 ---
    required_cols = {subject_col, object_col}
    if is_dynamic_predicate:
        predicate_entity_name, predicate_col = predicate_info
        predicate_lookup = lookups[predicate_entity_name]
        required_cols.add(predicate_col)
    
    try:
        df_relation = pd.read_csv(file_path, usecols=list(required_cols), dtype=str, low_memory=False)
        df_relation.dropna(inplace=True)
        
        print(f"\n正在处理关系: {os.path.basename(file_path)}...")
        count = 0
        
        for _, row in df_relation.iterrows():
            subject_name = subject_lookup.get(row[subject_col])
            
            if subject_name:
                # 获取谓语名称
                predicate_name = ""
                if is_dynamic_predicate:
                    predicate_name = predicate_lookup.get(row[predicate_col])
                else:
                    predicate_name = predicate_info

                # 获取宾语名称
                object_name = ""
                if object_is_literal:
                    object_name = row[object_col]
                else:
                    object_name = object_lookup.get(row[object_col])

                if predicate_name and object_name:
                    # 清理并写入
                    subject_name = str(subject_name).strip()
                    predicate_name = str(predicate_name).strip()
                    object_name = str(object_name).strip()
                    
                    if subject_name and predicate_name and object_name: # 确保三者都不为空
                        output_writer.writerow([subject_name, predicate_name, object_name])
                        count += 1
        
        print(f"成功提取 {count} 条三元组。")

    except Exception as e:
        print(f"错误: 处理 {file_path} 失败 - {e}")

# ==============================================================================
# 步骤 3: 主执行流程
# ==============================================================================

if __name__ == "__main__":
    # --- 1. 加载所有需要的实体查找字典 ---
    print("--- 开始加载实体查找字典 ---")
    all_lookups = {}
    for entity_name, config in ENTITY_CONFIG.items():
        file_path = os.path.join(BASE_DIR, config['file'])
        # 特别处理 BIOG_MAIN 的 ID 列，确保是字符串以便于查找
        if entity_name == 'Person':
            df = pd.read_csv(file_path, usecols=[config['id_col'], config['name_col']], dtype=str, low_memory=False)
            df.dropna(inplace=True)
            all_lookups[entity_name] = pd.Series(df[config['name_col']].values, index=df[config['id_col']]).to_dict()
            print(f"成功加载查找字典: {os.path.basename(file_path)} ({len(all_lookups[entity_name])} 条目)")
        else:
            all_lookups[entity_name] = load_lookup_dict(file_path, config['id_col'], config['name_col'])

    # --- 2. 准备输出文件并提取三元组 ---
    output_file_path = os.path.join(BASE_DIR, 'triples_person_attributes.csv')
    print(f"\n--- 开始提取人物基本属性三元组，结果将保存到: {output_file_path} ---")
    
    with open(output_file_path, 'w', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['Subject', 'Predicate', 'Object']) # 写入表头
        
        for rel_name, rel_info in RELATIONSHIP_CONFIG.items():
            extract_triples(rel_info, all_lookups, writer)
            
    print("\n--- 人物基本属性提取完成！---")
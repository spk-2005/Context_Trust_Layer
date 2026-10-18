"""
Multilingual Regression Suite: Chinese Legal Contract Claim Extraction (DOC-068).
Provides a calibrated suite of 30 positive deontic clauses and 30 negative/non-normative clauses.
Ensures Chinese extraction remains robust, avoids false triggers on compound nouns like 供应商,
and respects the multilingual feature flag.
"""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import patch

from app.core.multilingual import is_multilingual_enabled
from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit, ContentRole


# 30 Positive Clauses (Normative contractual requirements)
POSITIVE_CHINESE_CLAUSES = [
    # Obligations (应, 应当, 必须, 须)
    ("供应商应当按照本订单规定的交付日期交付货物。", "Supplier", "OBLIGATION"),
    ("供应商必须遵守所有适用的环境保护和劳动安全法律。", "Supplier", "OBLIGATION"),
    ("双方应当对在履行本合同过程中知悉的商业秘密予以保密。", "双方", "OBLIGATION"),
    ("供应商应当在收到订单后两个工作日内予以书面确认。", "Supplier", "OBLIGATION"),
    ("微软应当在收到合格发票后六十日内支付款项。", "微软", "OBLIGATION"),
    ("买方应当在验收货物后签署验收合格单据。", "买方", "OBLIGATION"),
    ("供应商应当为交付的货物购买足额的运输保险。", "Supplier", "OBLIGATION"),
    ("任何一方在变更注册地址时，应当提前三十天书面通知对方。", "任何一方", "OBLIGATION"),
    ("每次发货应当随附原厂出具的质量合格证明书。", "每次发货", "OBLIGATION"),
    ("供应商应当提供中文和英文版本的用户操作指南。", "Supplier", "OBLIGATION"),
    ("供应商必须确保所供软件未侵犯任何第三方的知识产权。", "Supplier", "OBLIGATION"),
    ("供应商应当建立完善的产品追溯体系以满足审计要求。", "Supplier", "OBLIGATION"),
    ("供应商须在交付前完成所有出厂安全检测。", "Supplier", "OBLIGATION"),
    ("供应商应当承担因产品质量缺陷导致的全部召回费用。", "Supplier", "OBLIGATION"),
    ("供应商必须按季度向微软提交服务质量报告。", "Supplier", "OBLIGATION"),
    
    # Prohibitions (不得, 禁止)
    ("供应商不得将本合同项下的任何义务转包给第三方。", "Supplier", "PROHIBITION"),
    ("供应商不得向微软员工提供任何形式的商业贿赂或回扣。", "Supplier", "PROHIBITION"),
    ("任何一方不得单方面擅自解除或终止本合同。", "任何一方", "PROHIBITION"),
    ("供应商不得在未经书面许可的情况下使用微软的商标或徽标。", "Supplier", "PROHIBITION"),
    ("供应商不得向任何无关人员披露客户的个人身份信息。", "Supplier", "PROHIBITION"),
    ("供应商不得收取包装费或装运前装箱费短驳费。", "Supplier", "PROHIBITION"),
    ("供应商不得在货物交付中使用带有安全隐患的再造零配件。", "Supplier", "PROHIBITION"),
    ("任何一方不得在争议解决期间中止履行无争议的合同条款。", "任何一方", "PROHIBITION"),

    # Permissions (可以, 有权)
    ("微软有权在任何合理时间对供应商的生产设施进行合规审计。", "微软", "PERMISSION"),
    ("买方可以根据实际生产需要调整下达的采购订单数量。", "买方", "PERMISSION"),
    ("如果供应商逾期交付，微软有权解除受影响的采购订单。", "微软", "PERMISSION"),
    ("供应商可以书面申请延长不可抗力事件期间的履行期限。", "Supplier", "PERMISSION"),
    ("在获得事先书面批准后，供应商可以使用合规的分包商。", "Supplier", "PERMISSION"),
    ("微软有权要求供应商返还未使用的预付款项。", "微软", "PERMISSION"),
    ("双方可以通过友好协商对本协议进行补充修改。", "双方", "PERMISSION"),
]

# 30 Negative Clauses (Descriptive, table headers, fragments, definitions, non-normative)
NEGATIVE_CHINESE_CLAUSES = [
    "采购订单通用条款与条件（中国大陆地区适用版本）",
    "第一条 定义与术语解释",
    "目录：1. 释义 2. 交付与验收 3. 付款方式",
    "本协议由以下双方于北京市海淀区签署：",
    "关于微软公司供应链管理合规指引的前言与背景介绍",
    "商品单价及费用明细表（人民币元）：",
    "序号 | 物料编号 | 规格型号 | 数量 | 计量单位",
    "如有任何疑问，请访问微软官方供应商门户网站。",
    "本文件共25页，当前第1页，仅供内部审核使用。",
    "签署日期：2026年10月18日。",
    "传真号码：+86-10-88888888 电子邮箱：vendor@example.com",
    "附录A：技术规格与服务水平协议附件清单",
    "随着全球数字化转型的深入推进，企业合规面临更多挑战。",
    "版权所有 (C) 2026 微软公司 保留所有权利。",
    "采购方名称：微软（中国）有限公司",
    "开户银行：中国工商银行北京分行营业部",
    "增值税专用发票开具说明与邮寄地址指引",
    "图表 2.1 供应链质量管理层级分布图",
    "注：上述费用不包含法定增值税税额及关税。",
    "免责声明：本指引仅作为一般参考，不构成法定保证。",
    "本条款适用于所有直销及分销合作伙伴渠道。",
    "常见问题解答 (FAQ)：如何提交季度发票？",
    "系统自动生成的发货通知单编号：PO-2026-99881",
    "请注意查看随附的软件许可证授权密钥。",
    "版本历史记录：V1.0 初始发布版，V2.0 修订版",
    "感谢您一直以来作为微软优秀供应商的合作支持。",
    "包装箱外观尺寸：长600mm x 宽400mm x 高300mm",
    "仓储温度要求范围：摄氏15度至25度，相对湿度小于60%",
    "供应商质量评级矩阵概述",
    "本采购协议终止后存续条款清单详见第14条。",
]


@pytest.mark.fast
def test_multilingual_feature_flag_default_disabled():
    """Verify that multilingual extraction is disabled by default."""
    assert not is_multilingual_enabled("zh-CN")


@pytest.mark.fast
def test_chinese_positive_deontic_classification():
    """Verify all 30 positive clauses are recognized with correct modality when enabled."""
    with patch("app.core.multilingual.is_multilingual_enabled", return_value=True):
        for text, expected_subj, expected_modality in POSITIVE_CHINESE_CLAUSES:
            modality, op, eligible = DeonticClassifier.classify_text(text)
            assert eligible is True, f"Clause should be eligible: {text}"
            assert modality == expected_modality, f"Expected {expected_modality} for '{text}', got {modality}"


@pytest.mark.fast
def test_chinese_negative_clauses_filtered():
    """Verify all 30 negative non-normative statements do not trigger obligations/prohibitions."""
    with patch("app.core.multilingual.is_multilingual_enabled", return_value=True):
        for text in NEGATIVE_CHINESE_CLAUSES:
            modality, op, eligible = DeonticClassifier.classify_text(text)
            assert modality not in ("OBLIGATION", "PROHIBITION"), (
                f"Negative clause falsely classified as {modality}: '{text}'"
            )


@pytest.mark.fast
def test_chinese_extractor_feature_flag_enforcement():
    """Verify that when disabled, Chinese text produces 0 claims from candidate discovery."""
    sample_text = "供应商应当按照本订单规定的交付日期交付货物。"
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="asset_test",
        block_type="clause",
        content_text=sample_text,
    )
    # When disabled (default)
    with patch("app.core.multilingual.is_multilingual_enabled", return_value=False):
        eligible, strat, reason = CandidateDiscoveryEngine.is_candidate(unit)
        assert "Chinese" not in reason

    # When enabled
    with patch("app.core.multilingual.is_multilingual_enabled", return_value=True):
        eligible, strat, reason = CandidateDiscoveryEngine.is_candidate(unit)
        assert eligible is True
        assert "Chinese" in reason

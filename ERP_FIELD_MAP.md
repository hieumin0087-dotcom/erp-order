# ERP Form Field Map - Verified by Live Browser Inspection (2026-05-20)
# Source: https://erp.bx123.pro/celebrityOrder/save

## SECTION 1: 网红信息 (Influencer Info)
| Label | HTML | id | Options/Notes |
|-------|------|----|---------------|
| 网名 | input | screenName | placeholder="网名" |
| 联络类型 | select | contactType | WhatsApp, Email, Phone, Instagram, Snapchat, Tiktok, Other |
| 联络方式 | input | contact | placeholder="联络方式" |
| 合作时间 | input | cooperationTime | Date picker, YYYY-MM-DD format |
| 合作状态 | select | cooperation | 新网红, 老网红 |
| 网红质量 | select | quality | 未知, 普通, 优质, 黑名单 |
| 联系邮箱 | input | email | Optional |
| 网红头像 | input[file] | avatarUploader | |

## SECTION 2: 社交账号 (Social Media)
| Label | HTML | id/selector | Options/Notes |
|-------|------|------------|---------------|
| 添加社交信息按钮 | button | addCelebritySocial | Must click first to add row |
| 平台 (in row) | select | no id, 1st select in tr | tiktok(default), Instagram, Facebook, YouTube, Pinterest, Twitter, Tumblr, Reddit |
| 社交账号 (in row) | input | no id | placeholder="社交账号" |
| 社交链接 (in row) | textarea | no id | placeholder="网红社交主页或推广详情页" |
| 粉丝数 (in row) | input | no id | placeholder="粉丝数" |
| 数量单位 (in row) | select | no id, 2nd select in tr | 单位...(placeholder), H, K, M |

## SECTION 3: 收货信息 (Shipping)
| Label | HTML | id | Notes |
|-------|------|----|-------|
| 姓名 | input | fullName | placeholder="收货人的真实姓名" |
| 电话 | input | phone | |
| 国家 | select | country | Format: "美国 [United States]" - match by English part |
| 省/州 | input | state | |
| 城市 | input | city | |
| 地址 | input | address | placeholder="详细地址" |
| 邮编 | input | zipCode | |
| 订单备注 | textarea | orderNote | Optional, max 255 chars |

## SECTION 4: 商品信息 (Product)
| Label | HTML | id | Notes |
|-------|------|----|-------|
| 商品链接 | input | goodsUrl | |
| 获取商品详情 | button | getGoodsInfo | Click to auto-fill name |
| 商品主图 | input[file] | goodsPosterUploader | |
| 商品细节图 | input[file] | goodsPictureUploader | Multiple files OK |
| 商品名称 | input | goodsName | |
| 商品品牌 | input | goodsBrand | |
| 商品类型 | select | goodsType | 包包, 鞋子, 配饰 |
| 属性(manual) | input | goodsSku | placeholder="如果右侧列表为空，可手工输入。" |
| 属性(dynamic) | select | goodsSkuList | Populated after getGoodsInfo click |

## SECTION 5: 推广效果 (Promotion)
| Label | HTML | id | Notes |
|-------|------|----|-------|
| 上线时间 | input | promoteOnlineTime | |
| 是否已上线 | radio | promoteOnlineStatus0/1 | 0=未上线(default), 1=已上线 |
| 效果状态 | radio | effectStatus0-3 | 0=未知, 1=差, 2=一般, 3=好 |
| 效果备注 | textarea | effectNote | |

## BUTTONS
| Label | HTML | id |
|-------|------|----|
| 保存订单 | button | doSave |
| 返回列表 | a | doReset |

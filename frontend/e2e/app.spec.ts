import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

test('registers, uploads a real PDF, streams, restores history and rejects another user', async ({ page, browser }) => {
  const suffix = `${Date.now()}_${Math.floor(Math.random() * 10000)}`;
  const username = `alice_${suffix}`;
  const name = `制度演示_${suffix}`;
  await page.goto('/');
  await page.getByRole('button', { name: '注册新账号' }).click();
  await page.getByLabel('用户名', { exact: true }).fill(username);
  await page.getByLabel('密码', { exact: true }).fill('test-password-123');
  await page.getByRole('button', { name: /创建账号$/ }).click();
  await expect(page.getByText('还没有知识库')).toBeVisible();
  await page.getByRole('button', { name: /创建知识库$/ }).click();
  await page.getByLabel('知识库名称').fill(name);
  await page.getByLabel('知识库描述').fill('浏览器验收使用仓库公开虚构制度');
  await page.getByRole('button', { name: '确认创建' }).click();
  await page.getByRole('button', { name: `打开知识库：${name}` }).click();
  await page.getByRole('link', { name: '文档管理', exact: true }).click();
  await page.getByLabel('上传 PDF').setInputFiles(path.join(root, 'data/demo_policies/pdfs/员工请假与考勤制度.pdf'));
  await expect(page.getByText('可检索', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '聊天工作台', exact: true }).click();
  await page.getByRole('button', { name: /新建会话$/ }).click();
  await page.getByLabel('输入问题').fill('员工请假需要怎样申请？');
  await page.getByRole('button', { name: '发送问题', exact: true }).click();
  const answer = '【测试模型】请按制度提前提交申请，并由负责人审批。';
  await expect(page.getByText(answer, { exact: true })).toBeVisible();
  const sourceButton = page.getByRole('button', { name: /查看来源（/ }).first();
  await sourceButton.click();
  await expect(page.getByText('回答来源', { exact: true })).toBeVisible();
  await expect(page.getByText('员工请假与考勤制度.pdf', { exact: true }).first()).toBeVisible();
  await page.keyboard.press('Escape');
  await page.reload();
  await expect(page.getByText(answer, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /查看来源（/ }).first()).toBeVisible();
  await page.screenshot({ path: path.join(root, 'artifacts/fullstack/workspace.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByLabel('输入问题')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(root, 'artifacts/fullstack/workspace-mobile.png'), fullPage: true });
  await page.setViewportSize({ width: 1280, height: 800 });

  const url = page.url();
  const kbId = /knowledge-bases\/(\d+)/.exec(url)![1];
  const conversationId = /\/chat\/(\d+)/.exec(url)![1];
  const second = await browser.newContext({ baseURL: 'http://localhost:5174' });
  try {
    const registration = await second.request.post('/api/auth/register', {
      data: { username: `bob_${suffix}`, password: 'test-password-123' },
    });
    expect(registration.status()).toBe(201);
    expect((await second.request.get(`/api/knowledge-bases/${kbId}`)).status()).toBe(404);
    expect((await second.request.get(`/api/knowledge-bases/${kbId}/documents`)).status()).toBe(404);
    expect((await second.request.get(`/api/conversations/${conversationId}/messages`)).status()).toBe(404);
    await expect((await second.request.get('/api/knowledge-bases')).json()).resolves.toEqual([]);
  } finally {
    await second.close();
  }

  await page.getByLabel('输入问题').fill('宇宙边界在哪里？');
  await page.getByRole('button', { name: '发送问题', exact: true }).click();
  await expect(page.getByText('当前知识库中没有找到足够的信息。', { exact: true })).toBeVisible();
  await page.getByLabel('输入问题').fill('中断验收：请解释请假制度');
  await page.getByRole('button', { name: '发送问题', exact: true }).click();
  await expect(page.getByText(/【测试模型】中断验收：/)).toBeVisible();
  await page.getByRole('button', { name: '停止生成', exact: true }).click();
  await expect.poll(async () => {
    const response = await page.request.get(`/api/conversations/${conversationId}/messages`);
    const messages = await response.json();
    return messages.at(-1)?.status;
  }).toBe('interrupted');
  await page.reload();
  await expect(page.getByText('已中断', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '退出登录', exact: true }).click();
  await expect(page.getByRole('button', { name: '登录工作台', exact: true })).toBeVisible();
  expect((await page.request.get('/api/knowledge-bases')).status()).toBe(401);
});

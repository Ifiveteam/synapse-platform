/**
 * Drive 폴더 연동 — GIS 코드 클라이언트 + Google Picker.
 *
 * 검증된 흐름(계정 정렬 필수):
 *   1) initCodeClient(popup)로 같은 계정 동의 → auth code
 *   2) 백엔드가 code 교환 → drive.file access token 반환 (계정 정렬됨)
 *   3) 그 access token으로 Picker 띄움 → 폴더 선택
 *   4) folder_id 백엔드 저장
 *
 * client_id / api_key는 브라우저 공개 안전 값(origin/referrer 제한으로 보호).
 */

import { connectDrive, saveDriveFolder } from "@/api/takeout";

const GIS_SRC = "https://accounts.google.com/gsi/client";
const GAPI_SRC = "https://apis.google.com/js/api.js";
const DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const API_KEY = import.meta.env.VITE_GOOGLE_PICKER_API_KEY as string | undefined;

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const el = document.createElement("script");
    el.src = src;
    el.async = true;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error(`스크립트 로드 실패: ${src}`));
    document.head.appendChild(el);
  });
}

/** GIS 코드 클라이언트로 drive.file 동의 → auth code */
async function getDriveAuthCode(): Promise<string> {
  if (!CLIENT_ID) throw new Error("VITE_GOOGLE_CLIENT_ID 미설정");
  await loadScript(GIS_SRC);
  const w = window as unknown as { google: any };
  return new Promise<string>((resolve, reject) => {
    const client = w.google.accounts.oauth2.initCodeClient({
      client_id: CLIENT_ID,
      scope: DRIVE_FILE_SCOPE,
      ux_mode: "popup",
      callback: (resp: { code?: string; error?: string }) => {
        if (resp.error || !resp.code) {
          reject(new Error(resp.error || "동의 취소됨"));
        } else {
          resolve(resp.code);
        }
      },
    });
    client.requestCode();
  });
}

/** access token으로 Picker를 띄워 폴더 1개 선택 */
async function openFolderPicker(
  accessToken: string,
): Promise<{ id: string; name: string }> {
  if (!API_KEY) throw new Error("VITE_GOOGLE_PICKER_API_KEY 미설정");
  await loadScript(GAPI_SRC);
  const w = window as unknown as { gapi: any; google: any };
  await new Promise<void>((res) => w.gapi.load("picker", res));

  return new Promise((resolve, reject) => {
    const view = new w.google.picker.DocsView(w.google.picker.ViewId.FOLDERS)
      .setSelectFolderEnabled(true)
      .setIncludeFolders(true);
    const picker = new w.google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(accessToken)
      .setDeveloperKey(API_KEY)
      .setCallback((data: { action: string; docs?: Array<{ id: string; name: string }> }) => {
        if (data.action === w.google.picker.Action.PICKED && data.docs?.[0]) {
          resolve({ id: data.docs[0].id, name: data.docs[0].name });
        } else if (data.action === w.google.picker.Action.CANCEL) {
          reject(new Error("폴더 선택 취소됨"));
        }
      })
      .build();
    picker.setVisible(true);
  });
}

/**
 * 전체 연동 1회 실행: 동의 → 토큰 교환 → Picker 폴더선택 → 저장.
 * 성공 시 선택한 폴더명을 반환한다.
 */
export async function connectDriveFolder(): Promise<{
  folderId: string;
  folderName: string;
}> {
  const code = await getDriveAuthCode();
  const { access_token } = await connectDrive(code);
  const folder = await openFolderPicker(access_token);
  await saveDriveFolder(folder.id, folder.name);
  return { folderId: folder.id, folderName: folder.name };
}

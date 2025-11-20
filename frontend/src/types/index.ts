export interface Portal {
  enabled: string;
  name: string;
  url: string;
  macs: { [mac: string]: string };
  'streams per mac': string;
  'epg offset': string;
  proxy: string;
  'enabled channels': string[];
  'custom channel names': { [id: string]: string };
  'custom channel numbers': { [id: string]: string };
  'custom genres': { [id: string]: string };
  'custom epg ids': { [id: string]: string };
  'fallback channels': { [id: string]: string };
}

export interface Portals {
  [portalId: string]: Portal;
}

export interface Channel {
  portal: string;
  portalName: string;
  enabled: boolean;
  channelNumber: string;
  customChannelNumber: string;
  channelName: string;
  customChannelName: string;
  genre: string;
  customGenre: string;
  channelId: string;
  customEpgId: string;
  fallbackChannel: string;
  link: string;
  duplicateCount: number;
}

export interface Settings {
  'stream method': string;
  'ffmpeg command': string;
  'ffmpeg timeout': string;
  'test streams': string;
  'try all macs': string;
  'use channel genres': string;
  'use channel numbers': string;
  'sort playlist by channel genre': string;
  'sort playlist by channel number': string;
  'sort playlist by channel name': string;
  'enable security': string;
  username: string;
  password: string;
  'enable hdhr': string;
  'hdhr name': string;
  'hdhr id': string;
  'hdhr tuners': string;
}

export interface Stream {
  mac: string;
  'channel id': string;
  'channel name': string;
  client: string;
  'portal name': string;
  'start time': number;
}

export interface StreamingData {
  [portalId: string]: Stream[];
}

export interface ChannelEdit {
  portal: string;
  'channel id': string;
  enabled?: boolean;
  'custom number'?: string;
  'custom name'?: string;
  'custom genre'?: string;
  'custom epg id'?: string;
  'channel name'?: string;
}

export interface DataTablesResponse {
  draw: number;
  recordsTotal: number;
  recordsFiltered: number;
  data: Channel[];
  error?: string;
}

